from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404, redirect

from .forms import MaintenanceRequestForm, CommentForm
from .models import *
from .serializers import *


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(requestor=self.request.user)

    @action(detail=True, methods=['post'])
    def upload_images(self, request, pk=None):
        maintenance_request = self.get_object()
        images = request.FILES.getlist('images')
        is_before = request.data.get('is_before_image', 'true').lower() == 'true'

        uploaded_images = []
        for image in images:
            maintenance_image = MaintenanceImage.objects.create(
                request=maintenance_request,
                image=image,
                is_before_image=is_before,
                caption=request.data.get('caption', '')
            )
            uploaded_images.append(MaintenanceImageSerializer(maintenance_image).data)

        return Response(uploaded_images, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def upload_completion_images(self, request, pk=None):
        maintenance_request = self.get_object()
        images = request.FILES.getlist('images')

        uploaded_images = []
        for image in images:
            completion_image = CompletionImage.objects.create(
                request=maintenance_request,
                image=image,
                caption=request.data.get('caption', '')
            )
            uploaded_images.append(CompletionImageSerializer(completion_image).data)

        return Response(uploaded_images, status=status.HTTP_201_CREATED)


class MaintenanceCategoryViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceCategory.objects.all()
    serializer_class = MaintenanceCategorySerializer


class MaintenanceListView(LoginRequiredMixin, ListView):
    model = MaintenanceRequest
    template_name = 'maintenance/list.html'
    context_object_name = 'maintenance_requests'

    def get_queryset(self):
        return MaintenanceRequest.objects.filter(requestor=self.request.user)


class MaintenanceCreateView(LoginRequiredMixin, CreateView):
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = 'maintenance/create.html'
    success_url = reverse_lazy('maintenance_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = MaintenanceCategory.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        form.instance.requestor = self.request.user
        response = super().form_valid(form)

        # Handle image uploads
        images = self.request.FILES.getlist('images')
        for image in images:
            MaintenanceImage.objects.create(
                request=self.object,
                image=image,
                is_before_image=True
            )

        return response


class MaintenanceDetailView(LoginRequiredMixin, DetailView):
    model = MaintenanceRequest
    template_name = 'maintenance/detail.html'
    context_object_name = 'maintenance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        return context

    def get_queryset(self):
        # ให้ดูได้เฉพาะรายการของตัวเอง
        return MaintenanceRequest.objects.filter(requestor=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # จัดการการอัพโหลดรูปภาพใหม่
        if 'new_images' in request.FILES:
            images = request.FILES.getlist('new_images')
            caption = request.POST.get('caption', '')

            for image in images:
                MaintenanceImage.objects.create(
                    request=self.object,
                    image=image,
                    caption=caption,
                    is_before_image=True
                )
            messages.success(request, 'อัพโหลดรูปภาพสำเร็จ')

        # จัดการการเพิ่มความคิดเห็น
        elif 'comment' in request.POST:
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.maintenance_request = self.object
                comment.user = request.user
                comment.save()
                messages.success(request, 'เพิ่มความคิดเห็นสำเร็จ')
            else:
                messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอก')

        return redirect('maintenance_detail', pk=self.object.pk)
