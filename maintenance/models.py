from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class MaintenanceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Maintenance Categories"

    def __str__(self):
        return self.name


class MaintenanceRequest(models.Model):
    # Add to MaintenanceRequest.STATUS_CHOICES
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),  # When technician is assigned
        ('EVALUATING', 'Evaluating'),  # When technician is evaluating
        ('EVALUATED', 'Evaluated'),  # After evaluation, before approval for repair
        ('APPROVED', 'Approved'),  # Approved to proceed with repair
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OUTSOURCED', 'Outsourced'),  # Requires external contractor
        ('TRANSFERRED', 'Transferred to Central'),  # Sent to central department
        ('NEED_PARTS', 'Waiting for Parts'),  # Needs parts before repair
        ('REJECTED', 'Rejected')
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent')
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(MaintenanceCategory, on_delete=models.PROTECT)
    requestor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='maintenance_requests')
    location = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.status}"

    @property
    def request_images(self):
        return self.images.all()

    permissions = [
        ("change_status", "Can change maintenance status"),
    ]


class MaintenanceImage(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='maintenance_images/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_before_image = models.BooleanField(default=True, help_text="True if image was taken before maintenance")

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.request.title} - {'Before' if self.is_before_image else 'After'}"


class CompletionImage(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='completion_images/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Completion image for {self.request.title}"


class MaintenanceAssignment(models.Model):
    """Model for tracking maintenance request assignments to technicians"""
    maintenance_request = models.ForeignKey('MaintenanceRequest', on_delete=models.CASCADE)
    technician = models.ForeignKey(User, on_delete=models.PROTECT, related_name='maintenance_assignments')
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='maintenance_assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']
        permissions = [
            ("can_assign_maintenance", "Can assign maintenance requests to technicians"),
        ]

    def __str__(self):
        return f"Assignment #{self.id} - {self.maintenance_request.title}"


class Parts(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity_in_stock = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=5)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name_plural = "Parts"

    def __str__(self):
        return self.name


class PartsRequest(models.Model):
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE)
    part = models.ForeignKey(Parts, on_delete=models.PROTECT)
    quantity_requested = models.IntegerField()
    approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.part.name} for {self.maintenance_request.title}"


class Comment(models.Model):
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.maintenance_request.title}"


class StatusLog(models.Model):
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, )
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    old_status = models.CharField(max_length=20, choices=MaintenanceRequest.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=MaintenanceRequest.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']


class Approval(models.Model):
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals_given')
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_approvals')
    note = models.TextField(blank=True)
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-approved_at']


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    maintenance_request = models.ForeignKey(
        'MaintenanceRequest',  # หรือชื่อโมเดลงานของคุณ
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def get_absolute_url(self):
        """สร้าง URL สำหรับดูรายละเอียดงาน"""
        if self.maintenance_request:
            return reverse('maintenance:maintenance_detail',
                           kwargs={'pk': self.maintenance_request.pk})
        return '#'


class UserProfile(models.Model):
    NOTIFICATION_CHOICES = [
        ('ALL', 'รับการแจ้งเตือนทั้งหมด'),
        ('EMAIL', 'อีเมลเท่านั้น'),
        ('LINE', 'Line เท่านั้น'),
        ('NONE', 'ไม่รับการแจ้งเตือน')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    line_token = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    notification_preferences = models.CharField(
        max_length=10,
        choices=NOTIFICATION_CHOICES,
        default='ALL'
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"


class RepairEvaluation(models.Model):
    EVALUATION_RESULT = [
        ('CAN_FIX', 'สามารถซ่อมได้'),
        ('OUTSOURCE', 'ต้องจ้างภายนอก'),
        ('CENTRAL_DEPT', 'ส่งกองกลาง'),
        ('NEED_PARTS', 'ต้องการอะไหล่ก่อนซ่อม'),
    ]

    maintenance_request = models.OneToOneField(MaintenanceRequest, on_delete=models.CASCADE, related_name='evaluation')
    technician = models.ForeignKey(User, on_delete=models.PROTECT)
    result = models.CharField(max_length=20, choices=EVALUATION_RESULT)
    notes = models.TextField(blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_time = models.IntegerField(help_text="Estimated time in hours", null=True, blank=True)
    parts_needed = models.TextField(blank=True, help_text="List of parts needed for repair")
    evaluated_at = models.DateTimeField(auto_now_add=True)

    # Add approval fields
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_maintenance_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True)
    approved_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Evaluation for {self.maintenance_request.title}"


class EvaluationImage(models.Model):
    evaluation = models.ForeignKey(RepairEvaluation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='evaluation_images/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for evaluation #{self.evaluation.id}"