import json

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView
from django.views.generic import TemplateView, ListView, UpdateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .forms import MaintenanceRequestForm, CommentForm
from .notifications import send_notification
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


def is_staff_check(user):
    return user.is_staff


@method_decorator(user_passes_test(is_staff_check), name='dispatch')
class MaintenanceManageView(ListView):
    model = MaintenanceRequest
    template_name = 'maintenance/manage.html'
    context_object_name = 'maintenance_requests'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = MaintenanceRequest.STATUS_CHOICES
        context['technicians'] = User.objects.filter(groups__name='Technicians')
        print(context['technicians'])
        return context


@require_http_methods(["POST"])
@user_passes_test(is_staff_check)
def update_status(request, pk):
    try:
        maintenance = MaintenanceRequest.objects.get(pk=pk)
        data = json.loads(request.body)
        _status = data.get('status')

        if status in dict(MaintenanceRequest.STATUS_CHOICES):
            maintenance.status = _status
            maintenance.save()

            # Create status change log
            StatusLog.objects.create(
                maintenance_request=maintenance,
                changed_by=request.user,
                old_status=maintenance.status,
                new_status=_status
            )

            return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
@user_passes_test(is_staff_check)
def approve_request(request, pk):
    try:
        maintenance = MaintenanceRequest.objects.get(pk=pk)
        data = json.loads(request.body)

        technician_id = data.get('technician_id')
        note = data.get('note', '')

        technician = User.objects.get(pk=technician_id)
        print(technician,technician_id)

        maintenance.assigned_technician = technician
        maintenance.status = 'APPROVED'
        maintenance.save()

        # Create approval record
        Approval.objects.create(
            maintenance_request=maintenance,
            approved_by=request.user,
            technician=technician,
            note=note
        )

        # Send notification to technician
        send_notification(
            user_id=technician.id,
            title='งานซ่อมใหม่',
            message=f'คุณได้รับมอบหมายงานซ่อม: {maintenance.title}'
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'maintenance/profile.html'
    model = User
    fields = ['first_name', 'last_name', 'email']

    def get_object(self):
        return self.request.user


class SettingsView(LoginRequiredMixin, UpdateView):
    template_name = 'maintenance/settings.html'
    model = UserProfile
    fields = ['line_token', 'phone_number', 'notification_preferences']

    def get_object(self):
        return self.request.user.userprofile


class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'maintenance/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add reports data
        return context


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'maintenance/notifications.html'
    model = Notification
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


# API Views
@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def get_unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def export_reports(request):
    # Export logic here
    pass


@login_required
def filter_maintenance(request):
    # Filtering logic here
    pass


@login_required
def get_technicians(request):
    technicians = User.objects.filter(groups__name='Technicians')
    data = [{'id': tech.id, 'name': tech.get_full_name()} for tech in technicians]
    return JsonResponse(data, safe=False)


# @login_required
# def get_departments(request):
#     departments = Department.objects.all()
#     data = [{'id': dept.id, 'name': dept.name} for dept in departments]
#     return JsonResponse(data, safe=False)
