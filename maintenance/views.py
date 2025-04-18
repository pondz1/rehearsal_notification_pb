import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.generic import CreateView, DetailView
from django.views.generic import TemplateView, ListView, UpdateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .forms import MaintenanceRequestForm, CommentForm, UserForm, UserProfileForm
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
    success_url = reverse_lazy('maintenance:maintenance_list')

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

    def get_queryset(self):
        base_query = MaintenanceRequest.objects.all()  # เริ่มต้นด้วย all()

        # ถ้าไม่ใช่ staff จะกรองเฉพาะรายการที่เกี่ยวข้อง
        if not self.request.user.is_staff:
            base_query = base_query.filter(
                Q(requestor=self.request.user) |  # ผู้แจ้งซ่อม
                Q(maintenanceassignment__technician=self.request.user)  # ช่างที่ได้รับมอบหมาย
            )

        # เพิ่ม prefetch_related สำหรับข้อมูลที่เกี่ยวข้อง
        return base_query.prefetch_related(
            'images',
            'comments',
            'comments__user',
            'maintenanceassignment_set'
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        maintenance = self.object

        # ดึงข้อมูลการมอบหมายงานล่าสุด
        assignment = maintenance.maintenanceassignment_set.first()
        status_allows_edit = maintenance.status not in ['COMPLETED', 'REJECTED']
        status_allows_approve = maintenance.status in ['EVALUATED']

        context.update({
            'comment_form': CommentForm(),
            'is_requestor': maintenance.requestor == self.request.user,
            'is_technician': assignment and assignment.technician == self.request.user,
            'can_edit': (self.request.user.is_staff or maintenance.requestor == self.request.user) and status_allows_edit,
            'can_approve': self.request.user.has_perm('maintenance.approve_maintenancerequest') and status_allows_approve,
            'before_images': maintenance.images.filter(is_before_image=True),
            'after_images': maintenance.images.filter(is_before_image=False),
            'current_assignment': assignment,
            'status_logs': maintenance.statuslog_set.all().order_by('-changed_at'),
            'technicians': User.objects.filter(groups__name='Technicians'),
        })

        # เช็คว่าผู้ใช้เป็นช่างที่ได้รับมอบหมายหรือไม่
        is_assigned_technician = assignment and assignment.technician == self.request.user

        # เช็คว่ารายการนี้มีการประเมินแล้วหรือยัง
        has_evaluation = hasattr(maintenance, 'evaluation')

        # เช็คสถานะที่อนุญาตให้ประเมินได้
        can_evaluate = is_assigned_technician and maintenance.status in ['ASSIGNED',
                                                                         'EVALUATING'] and not has_evaluation

        # เพิ่มข้อมูลเกี่ยวกับการประเมิน
        context.update({
            'is_assigned_technician': is_assigned_technician,
            'can_evaluate': can_evaluate,
            'has_evaluation': has_evaluation,
            'evaluation': getattr(maintenance, 'evaluation', None),
            'evaluation_results': RepairEvaluation.EVALUATION_RESULT,
        })

        if hasattr(self.object, 'evaluation') and self.object.evaluation.parts_needed:
            context['parts_list'] = self.object.evaluation.parts_needed.strip().split('\n')

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        _action = request.POST.get('action')

        if _action == 'upload_images':
            return self._handle_image_upload(request)
        elif _action == 'add_comment':
            return self._handle_comment(request)
        elif _action == 'update_status':
            return self._handle_status_update(request)
        elif _action == 'approve_request':
            return self._handle_approval(request)
        elif _action == 'evaluate_request':
            return self._handle_evaluation(request)

        messages.error(request, 'การดำเนินการไม่ถูกต้อง')
        return redirect('maintenance:maintenance_detail', pk=self.object.pk)

    def _handle_evaluation(self, request):
        # ตรวจสอบว่าผู้ใช้เป็นช่างที่ได้รับมอบหมายหรือไม่
        assignment = self.object.maintenanceassignment_set.filter(technician=request.user).first()
        if not assignment:
            messages.error(request, 'คุณไม่ได้รับมอบหมายให้ประเมินงานนี้')
            return redirect('maintenance:maintenance_detail', pk=self.object.pk)

        # ตรวจสอบว่าสามารถประเมินได้หรือไม่
        if self.object.status not in ['ASSIGNED', 'EVALUATING'] or hasattr(self.object, 'evaluation'):
            messages.error(request, 'ไม่สามารถประเมินงานนี้ได้')
            return redirect('maintenance:maintenance_detail', pk=self.object.pk)

        # ดำเนินการประเมิน
        result = request.POST.get('result')
        if result not in dict(RepairEvaluation.EVALUATION_RESULT):
            messages.error(request, 'ผลการประเมินไม่ถูกต้อง')
            return redirect('maintenance:maintenance_detail', pk=self.object.pk)

        # สร้างบันทึกการประเมิน
        evaluation = RepairEvaluation.objects.create(
            maintenance_request=self.object,
            technician=request.user,
            result=result,
            notes=request.POST.get('notes', ''),
            estimated_cost=request.POST.get('estimated_cost') or None,
            estimated_time=request.POST.get('estimated_time') or None,
            parts_needed=request.POST.get('parts_needed', '')
        )

        # อัพโหลดรูปภาพประกอบการประเมิน (ถ้ามี)
        if 'evaluation_images' in request.FILES:
            images = request.FILES.getlist('evaluation_images')
            for image in images:
                EvaluationImage.objects.create(
                    evaluation=evaluation,
                    image=image,
                    caption=request.POST.get('image_caption', '')
                )

        # อัพเดทสถานะตามผลการประเมิน
        old_status = self.object.status
        if result == 'CAN_FIX':
            self.object.status = 'EVALUATED'
        elif result == 'OUTSOURCE':
            self.object.status = 'OUTSOURCED'
        elif result == 'CENTRAL_DEPT':
            self.object.status = 'TRANSFERRED'
        elif result == 'NEED_PARTS':
            self.object.status = 'NEED_PARTS'

        self.object.save()

        # บันทึกประวัติการเปลี่ยนสถานะ
        StatusLog.objects.create(
            maintenance_request=self.object,
            changed_by=request.user,
            old_status=old_status,
            new_status=self.object.status
        )

        # สร้างการแจ้งเตือน
        self._create_evaluation_notification(evaluation)

        messages.success(request, 'บันทึกการประเมินสำเร็จ')
        return redirect('maintenance:maintenance_detail', pk=self.object.pk)

    def _create_evaluation_notification(self, evaluation):
        maintenance = self.object

        # แจ้งเตือนผู้แจ้งซ่อม
        send_notification(
            user_id=maintenance.requestor.id,
            title=f"งานซ่อมได้รับการประเมินแล้ว",
            message=f"งานซ่อม {maintenance.title} ได้รับการประเมินจากช่างแล้ว - {dict(RepairEvaluation.EVALUATION_RESULT)[evaluation.result]}",
            maintenance_request=maintenance
        )

        # แจ้งเตือนผู้ดูแลระบบ/ผู้จัดการ
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            if admin.id != evaluation.technician.id:  # ไม่ส่งให้ช่างที่ประเมิน
                send_notification(
                    user_id=admin.id,
                    title=f"มีการประเมินงานซ่อมใหม่",
                    message=f"งานซ่อม {maintenance.title} ได้รับการประเมินแล้ว - {dict(RepairEvaluation.EVALUATION_RESULT)[evaluation.result]}",
                    maintenance_request=maintenance
                )

    def _handle_image_upload(self, request):
        if 'images' not in request.FILES:
            messages.error(request, 'กรุณาเลือกรูปภาพ')
            return redirect('maintenance:maintenance_detail', pk=self.object.pk)

        images = request.FILES.getlist('images')
        caption = request.POST.get('caption', '')
        is_before = request.POST.get('image_type') == 'before'

        for image in images:
            MaintenanceImage.objects.create(
                request=self.object,
                image=image,
                caption=caption,
                is_before_image=is_before,
            )

        messages.success(request, 'อัพโหลดรูปภาพสำเร็จ')
        return redirect('maintenance:maintenance_detail', pk=self.object.pk)

    def _handle_comment(self, request):
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.maintenance_request = self.object
            comment.user = request.user
            comment.save()

            # สร้างการแจ้งเตือนสำหรับผู้ที่เกี่ยวข้อง
            self._create_comment_notification(comment)

            messages.success(request, 'เพิ่มความคิดเห็นสำเร็จ')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอก')
        return redirect('maintenance:maintenance_detail', pk=self.object.pk)

    def _handle_status_update(self, request):
        # if not request.user.has_perm('maintenance.change_status'):
        #     messages.error(request, 'คุณไม่มีสิทธิ์ในการเปลี่ยนสถานะ')
        #     return redirect('maintenance:maintenance_detail', pk=self.object.pk)

        new_status = request.POST.get('status')
        if new_status in dict(MaintenanceRequest.STATUS_CHOICES):
            old_status = self.object.status
            self.object.status = new_status
            self.object.save()

            # บันทึกประวัติการเปลี่ยนสถานะ
            StatusLog.objects.create(
                maintenance_request=self.object,
                changed_by=request.user,
                old_status=old_status,
                new_status=new_status
            )

            messages.success(request, 'อัพเดทสถานะสำเร็จ')
        else:
            messages.error(request, 'สถานะไม่ถูกต้อง')
        return redirect('maintenance:maintenance_detail', pk=self.object.pk)

    def _create_comment_notification(self, comment):
        maintenance = self.object
        recipients = {maintenance.requestor}

        # เพิ่มช่างที่ได้รับมอบหมายในการแจ้งเตือน
        assignment = maintenance.maintenanceassignment_set.first()
        if assignment:
            recipients.add(assignment.technician)

        # ไม่ส่งการแจ้งเตือนถึงผู้แสดงความคิดเห็นเอง
        recipients.discard(comment.user)

        for recipient in recipients:
            send_notification(
                user_id=recipient.id,
                title=f"ความคิดเห็นใหม่ในงานซ่อมบำรุง #{maintenance.id}",
                message=f"{comment.user.get_full_name()} ได้แสดงความคิดเห็น: {comment.content[:100]}...",
                maintenance_request=maintenance
            )


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

class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'maintenance/profile.html'
    form_class = UserForm
    success_url = reverse_lazy('maintenance:profile')

    def get_object(self, **kwargs):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'โปรไฟล์ถูกอัพเดทเรียบร้อยแล้ว')
        return super().form_valid(form)


class SettingsView(LoginRequiredMixin, UpdateView):
    template_name = 'maintenance/settings.html'
    form_class = UserProfileForm
    success_url = reverse_lazy('maintenance:settings')

    def get_object(self, **kwargs):
        return self.request.user.userprofile

    def form_valid(self, form):
        messages.success(self.request, 'การตั้งค่าถูกบันทึกเรียบร้อยแล้ว')
        return super().form_valid(form)


class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'maintenance/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = datetime.now()
        last_30_days = today - timedelta(days=30)
        requests = MaintenanceRequest.objects.all()

        # อัพเดตการ query ให้ตรงกับ STATUS_CHOICES
        context.update({
            'total_requests': requests.count(),
            'pending_requests': requests.filter(status='PENDING').count(),
            'approved_requests': requests.filter(status='APPROVED').count(),
            'in_progress_requests': requests.filter(status='IN_PROGRESS').count(),
            'completed_requests': requests.filter(status='COMPLETED').count(),
            'rejected_requests': requests.filter(status='REJECTED').count(),
        })

        # ปรับปรุงการ query monthly data
        monthly_data = []
        for month in range(1, 13):
            month_requests = requests.filter(
                created_at__year=today.year,
                created_at__month=month
            )

            month_stats = {
                'created_at__month': month,
                'total': month_requests.count(),
                'pending': month_requests.filter(status='PENDING').count(),
                'approved': month_requests.filter(status='APPROVED').count(),
                'in_progress': month_requests.filter(status='IN_PROGRESS').count(),
                'completed': month_requests.filter(status='COMPLETED').count(),
                'rejected': month_requests.filter(status='REJECTED').count()
            }
            monthly_data.append(month_stats)

        context['monthly_stats_json'] = json.dumps(monthly_data)
        context['requests_by_category'] = requests.values('category__name') \
            .annotate(count=Count('id')) \
            .order_by('-count')
        return context


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 10  # จำนวนการแจ้งเตือนต่อหน้า

    def get_queryset(self):
        # ดึงเฉพาะการแจ้งเตือนของผู้ใช้ที่ login
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # อัพเดทสถานะว่าผู้ใช้ได้เห็นการแจ้งเตือนแล้ว
        unread_notifications = self.get_queryset().filter(is_read=False)
        unread_notifications.update(
            is_read=True,
            read_at=timezone.now()
        )
        # เพิ่มจำนวนการแจ้งเตือนที่ยังไม่ได้อ่าน
        context['unread_count'] = self.request.user.notifications.filter(
            is_read=False
        ).count()
        return context


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


class MaintenanceRequestEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = MaintenanceRequest
    template_name = 'maintenance/edit.html'
    fields = ['title', 'description', 'category', 'location', 'priority']

    def test_func(self):
        maintenance = self.get_object()
        # อนุญาตให้แก้ไขได้เฉพาะผู้แจ้งหรือผู้ดูแลระบบ
        # และสถานะต้องยังไม่เป็น COMPLETED หรือ REJECTED
        can_edit = (self.request.user == maintenance.requestor or
                    self.request.user.is_staff)
        status_allows_edit = maintenance.status not in ['COMPLETED', 'REJECTED']
        return can_edit and status_allows_edit

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['description'].widget.attrs.update({
            'rows': 4
        })
        return form

    def get_success_url(self):
        return reverse_lazy('maintenance:maintenance_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        return response


@login_required
def evaluate_request(request, pk):
    maintenance = MaintenanceRequest.objects.get(pk=pk)
    assignment = maintenance.maintenanceassignment_set.filter(technician=request.user).first()

    # ตรวจสอบว่าผู้ใช้เป็นช่างที่ได้รับมอบหมายหรือไม่
    if not assignment:
        messages.error(request, 'คุณไม่ได้รับมอบหมายให้ประเมินงานนี้')
        return redirect('maintenance:maintenance_detail', pk=maintenance.pk)

    # ตรวจสอบสถานะว่าสามารถประเมินได้หรือไม่
    if maintenance.status not in ['ASSIGNED', 'EVALUATING'] or hasattr(maintenance, 'evaluation'):
        messages.error(request, 'ไม่สามารถประเมินงานนี้ได้')
        return redirect('maintenance:maintenance_detail', pk=maintenance.pk)

    if request.method == 'POST':
        # ดำเนินการประเมินงาน
        result = request.POST.get('result')
        if result not in dict(RepairEvaluation.EVALUATION_RESULT):
            messages.error(request, 'ผลการประเมินไม่ถูกต้อง')
            return redirect('maintenance:maintenance_detail', pk=maintenance.pk)

        # สร้างบันทึกการประเมิน
        evaluation = RepairEvaluation.objects.create(
            maintenance_request=maintenance,
            technician=request.user,
            result=result,
            notes=request.POST.get('notes', ''),
            estimated_cost=request.POST.get('estimated_cost') or None,
            estimated_time=request.POST.get('estimated_time') or None,
            parts_needed=request.POST.get('parts_needed', '')
        )

        # อัพโหลดรูปภาพประกอบการประเมิน (ถ้ามี)
        images = request.FILES.getlist('evaluation_images')
        for image in images:
            EvaluationImage.objects.create(
                evaluation=evaluation,
                image=image,
                caption=request.POST.get('image_caption', '')
            )

        # อัพเดทสถานะตามผลการประเมิน
        old_status = maintenance.status
        if result == 'CAN_FIX':
            maintenance.status = 'EVALUATED'
        elif result == 'OUTSOURCE':
            maintenance.status = 'OUTSOURCED'
        elif result == 'CENTRAL_DEPT':
            maintenance.status = 'TRANSFERRED'
        elif result == 'NEED_PARTS':
            maintenance.status = 'NEED_PARTS'

        maintenance.save()

        # บันทึกประวัติการเปลี่ยนสถานะ
        StatusLog.objects.create(
            maintenance_request=maintenance,
            changed_by=request.user,
            old_status=old_status,
            new_status=maintenance.status
        )

        # สร้างการแจ้งเตือนสำหรับการประเมิน
        send_notification(
            user_id=maintenance.requestor.id,
            title=f"งานซ่อมได้รับการประเมินแล้ว",
            message=f"งานซ่อม {maintenance.title} ได้รับการประเมินจากช่างแล้ว - {dict(RepairEvaluation.EVALUATION_RESULT)[result]}",
            maintenance_request=maintenance
        )

        # แจ้งเตือนผู้ดูแลระบบ/ผู้จัดการเกี่ยวกับผลการประเมิน
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            send_notification(
                user_id=admin.id,
                title=f"มีการประเมินงานซ่อมใหม่",
                message=f"งานซ่อม {maintenance.title} ได้รับการประเมินแล้ว - {dict(RepairEvaluation.EVALUATION_RESULT)[result]}",
                maintenance_request=maintenance
            )

        messages.success(request, 'บันทึกการประเมินสำเร็จ')
        return redirect('maintenance:maintenance_detail', pk=maintenance.pk)

    # กรณี GET request แสดงฟอร์มประเมิน
    return render(request, 'maintenance/evaluate.html', {
        'maintenance': maintenance,
        'evaluation_results': RepairEvaluation.EVALUATION_RESULT,
    })


@login_required
@require_POST
def assign_maintenance_request(request, request_id):
    """
    API endpoint for assigning a maintenance request to a technician
    """
    # Check if user has permission to assign maintenance requests
    if not request.user.has_perm('maintenance.can_assign_maintenance'):
        return JsonResponse({
            'success': False,
            'error': 'ไม่มีสิทธิ์ในการมอบหมายงานซ่อม'
        }, status=403)

    # Get the maintenance request
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)

    # Check if the request is in a valid state for assignment
    if maintenance_request.status != 'PENDING':
        return JsonResponse({
            'success': False,
            'error': 'ไม่สามารถมอบหมายงานซ่อมที่ไม่อยู่ในสถานะรอดำเนินการ'
        }, status=400)

    try:
        # Parse request data
        data = json.loads(request.body)
        technician_id = data.get('technician_id')
        note = data.get('note', '')

        # Get the technician
        technician = get_object_or_404(User, id=technician_id)

        # Check if technician has the right role
        if not technician.groups.filter(name='Technicians').exists():
            return JsonResponse({
                'success': False,
                'error': 'ผู้ใช้ที่เลือกไม่ใช่ช่างซ่อม'
            }, status=400)
        old_status = maintenance_request.status
        # Update the maintenance request status
        maintenance_request.status = 'ASSIGNED'
        maintenance_request.save()

        # Create assignment
        assignment = MaintenanceAssignment.objects.create(
            maintenance_request=maintenance_request,
            technician=technician,
            assigned_by=request.user,
            note=note
        )

        StatusLog.objects.create(
            maintenance_request=maintenance_request,
            changed_by=request.user,
            old_status=old_status,
            new_status=maintenance_request.status,
        )
        # Send notification to technician
        send_notification(
            user_id=technician.id,
            title='มอบหมายงานซ่อม',
            message=f'คุณได้รับมอบหมายงานซ่อม: {maintenance_request.title}',
            maintenance_request=maintenance_request,
        )

        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'มอบหมายงานซ่อมสำเร็จ',
            'assignment_id': assignment.id
        })

    except Exception as e:
        # Log the error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error assigning maintenance request: {str(e)}")

        # Return error response
        return JsonResponse({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }, status=500)

@login_required
@require_GET
def get_maintenance_evaluation(request, request_id):
    """API endpoint to get evaluation details for a maintenance request"""
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)

    # Get evaluation if it exists
    evaluation = maintenance_request.evaluation if hasattr(maintenance_request, 'evaluation') else None

    if not evaluation:
        return JsonResponse({
            'success': False,
            'error': 'ยังไม่มีการประเมินสำหรับงานซ่อมนี้'
        }, status=404)

    # Return evaluation details
    return JsonResponse({
        'success': True,
        'estimated_cost': evaluation.estimated_cost,
        'estimated_hours': evaluation.estimated_time,
        'parts_needed': evaluation.parts_needed,
        'result': evaluation.result,
        'result_display': evaluation.get_result_display(),
    })

@login_required
@permission_required('maintenance.can_approve_maintenance')
@require_POST
def approve_repair(request, request_id):
    """API endpoint for approving a repair after evaluation"""
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)

    # Validate request is in the correct state
    if maintenance_request.status != 'EVALUATED':
        return JsonResponse({
            'success': False,
            'error': 'สามารถอนุมัติได้เฉพาะงานซ่อมที่ประเมินแล้วเท่านั้น'
        }, status=400)

    try:
        data = json.loads(request.body)
        approved_budget = data.get('approved_budget', 0)
        note = data.get('note', '')

        # Update the evaluation with approval details
        evaluation = maintenance_request.evaluation
        evaluation.approved_budget = approved_budget
        evaluation.approval_notes = note
        evaluation.approved_at = timezone.now()
        evaluation.approved_by = request.user
        evaluation.save()

        assignment = maintenance_request.maintenanceassignment_set.first()

        old_status = maintenance_request.status

        # Update request status
        maintenance_request.status = 'APPROVED'
        maintenance_request.save()

        Approval.objects.create(
            maintenance_request=maintenance_request,
            approved_by=request.user,
            technician=assignment.technician,
            note=note
        )

        StatusLog.objects.create(
            maintenance_request=maintenance_request,
            changed_by=request.user,
            old_status=old_status,
            new_status=maintenance_request.status,
        )

        # Send notification to technician
        send_notification(
            user_id=assignment.technician.id,
            title='อนุมัติงาน',
            message=f'งานซ่อม {maintenance_request.title} ได้รับการอนุมัติแล้ว สามารถเริ่มงานได้เลย',
            maintenance_request=maintenance_request,
        )

        return JsonResponse({
            'success': True
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'รูปแบบข้อมูลไม่ถูกต้อง'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@permission_required('maintenance.can_approve_maintenance')
@require_POST
def approve_parts(request, request_id):
    """API endpoint for approving parts purchase for a maintenance request"""
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)

    # Validate request is in the correct state
    if maintenance_request.status != 'NEED_PARTS':
        return JsonResponse({
            'success': False,
            'error': 'สามารถอนุมัติการซื้ออะไหล่ได้เฉพาะงานที่รอจัดซื้ออะไหล่เท่านั้น'
        }, status=400)

    try:
        data = json.loads(request.body)
        approved_budget = data.get('approved_budget', 0)
        note = data.get('note', '')

        # Update the evaluation with approval details
        evaluation = maintenance_request.evaluation
        evaluation.approved_budget = approved_budget
        evaluation.approval_notes = note
        evaluation.approved_at = timezone.now()
        evaluation.approved_by = request.user
        evaluation.save()

        # Update request status to indicate parts are being ordered
        maintenance_request.status = 'APPROVED'
        maintenance_request.save()

        return JsonResponse({
            'success': True
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'รูปแบบข้อมูลไม่ถูกต้อง'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)