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
        ('PENDING', 'รอดำเนินการ'),
        ('ASSIGNED', 'มอบหมายแล้ว'),  # เมื่อช่างเทคนิคได้รับมอบหมาย
        ('EVALUATING', 'กำลังประเมิน'),  # เมื่อช่างเทคนิคกำลังประเมิน
        ('EVALUATED', 'ประเมินแล้ว'),  # หลังจากประเมิน ก่อนอนุมัติการซ่อม
        ('APPROVED', 'อนุมัติแล้ว'),  # อนุมัติให้ดำเนินการซ่อม
        ('IN_PROGRESS', 'กำลังดำเนินการ'),
        ('COMPLETED', 'เสร็จสมบูรณ์'),
        ('OUTSOURCED', 'จ้างภายนอก'),  # ต้องการผู้รับเหมาภายนอก
        ('TRANSFERRED', 'ส่งต่อไปส่วนกลาง'),  # ส่งไปยังแผนกส่วนกลาง
        ('NEED_PARTS', 'รออะไหล่'),  # ต้องการอะไหล่ก่อนการซ่อม
        ('REJECTED', 'ปฏิเสธ')
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'ต่ำ'),
        ('MEDIUM', 'ปานกลาง'),
        ('HIGH', 'สูง'),
        ('URGENT', 'เร่งด่วน')
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
        ('CAN_FIX', 'ซ่อมได้เอง'),
        ('OUTSOURCE', 'จ้างภายนอก'),
        ('CENTRAL_DEPT', 'ช่างกองกลาง'),
        ('NEED_PARTS', 'ซ่อมได้ (ต้องการอะไหล่)'),
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

# โมเดลสำหรับอะไหล่/วัสดุ
class Part(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่ออะไหล่")
    description = models.TextField(blank=True, verbose_name="รายละเอียด")
    part_number = models.CharField(max_length=50, blank=True, verbose_name="รหัสอะไหล่")
    unit = models.CharField(max_length=50, default="ชิ้น", verbose_name="หน่วยนับ")  # เช่น ชิ้น, อัน, กล่อง
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ราคาต่อหน่วย")
    stock_quantity = models.IntegerField(default=0, verbose_name="จำนวนในคลัง")
    minimum_stock = models.IntegerField(default=0, verbose_name="จำนวนขั้นต่ำที่ควรมี")
    category = models.CharField(max_length=100, blank=True, verbose_name="หมวดหมู่")

    class Meta:
        verbose_name = "อะไหล่"
        verbose_name_plural = "อะไหล่"

    def __str__(self):
        return f"{self.name} ({self.part_number})" if self.part_number else self.name

    @property
    def needs_reorder(self):
        return self.stock_quantity <= self.minimum_stock


# โมเดลสำหรับผู้ขาย/ซัพพลายเออร์
class Vendor(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อผู้ขาย")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="ชื่อผู้ติดต่อ")
    phone = models.CharField(max_length=50, blank=True, verbose_name="เบอร์โทรศัพท์")
    email = models.EmailField(blank=True, verbose_name="อีเมล")
    address = models.TextField(blank=True, verbose_name="ที่อยู่")
    tax_id = models.CharField(max_length=20, blank=True, verbose_name="เลขประจำตัวผู้เสียภาษี")
    is_active = models.BooleanField(default=True, verbose_name="สถานะ")
    notes = models.TextField(blank=True, verbose_name="หมายเหตุ")

    class Meta:
        verbose_name = "ผู้ขาย"
        verbose_name_plural = "ผู้ขาย"

    def __str__(self):
        return self.name


# โมเดลสำหรับใบขอซื้อ (PR)
class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'แบบร่าง'),
        ('PENDING', 'รออนุมัติ'),
        ('APPROVED', 'อนุมัติแล้ว'),
        ('REJECTED', 'ปฏิเสธ'),
        ('CONVERTED', 'แปลงเป็น PO แล้ว')
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'ต่ำ'),
        ('MEDIUM', 'ปานกลาง'),
        ('HIGH', 'สูง'),
        ('URGENT', 'เร่งด่วน')
    ]

    pr_number = models.CharField(max_length=20, unique=True, verbose_name="เลขที่ PR")
    maintenance_request = models.ForeignKey('MaintenanceRequest', on_delete=models.CASCADE,
                                            related_name='purchase_requests', verbose_name="งานซ่อม")
    evaluation = models.ForeignKey('RepairEvaluation', on_delete=models.CASCADE,
                                   verbose_name="ผลการประเมิน")
    title = models.CharField(max_length=200, verbose_name="หัวข้อ")
    description = models.TextField(blank=True, verbose_name="รายละเอียด")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES,
                                default='MEDIUM', verbose_name="ความเร่งด่วน")

    # ผู้รับผิดชอบ
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                     related_name='purchase_requests', verbose_name="ผู้ขอซื้อ")
    department = models.CharField(max_length=100, verbose_name="แผนก")

    # สถานะและวันที่
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="สถานะ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่แก้ไขล่าสุด")

    # ข้อมูลการอนุมัติ
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='approved_prs', null=True, blank=True,
                                    verbose_name="ผู้อนุมัติ")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="วันที่อนุมัติ")
    rejection_reason = models.TextField(blank=True, verbose_name="เหตุผลที่ปฏิเสธ")

    # ข้อมูลงบประมาณ
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="จำนวนเงินรวม")
    budget_code = models.CharField(max_length=50, blank=True, verbose_name="รหัสงบประมาณ")

    class Meta:
        verbose_name = "ใบขอซื้อ"
        verbose_name_plural = "ใบขอซื้อ"
        permissions = [
            ("approve_pr", "Can approve purchase requests"),
            ("reject_pr", "Can reject purchase requests"),
        ]

    def __str__(self):
        return f"{self.pr_number} - {self.title}"

    def save(self, *args, **kwargs):
        # สร้างเลขที่ PR อัตโนมัติถ้ายังไม่มี
        if not self.pr_number:
            prefix = "PR"
            year = timezone.now().strftime('%y')
            month = timezone.now().strftime('%m')

            # หาเลขลำดับล่าสุดของเดือนนี้
            last_pr = PurchaseRequest.objects.filter(
                pr_number__startswith=f"{prefix}{year}{month}"
            ).order_by('-pr_number').first()

            if last_pr:
                # ตัดเอาเฉพาะเลขลำดับท้าย 4 ตัว
                last_num = int(last_pr.pr_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1

            # สร้างเลขที่ PR ใหม่
            self.pr_number = f"{prefix}{year}{month}{new_num:04d}"

        super().save(*args, **kwargs)

        # อัพเดทยอดรวมอัตโนมัติ
        self.update_total()

    def update_total(self):
        total = sum(item.total_price for item in self.items.all())
        if self.total_amount != total:
            self.total_amount = total
            # ใช้ update เพื่อไม่ให้เรียก save อีกรอบ
            PurchaseRequest.objects.filter(id=self.id).update(total_amount=total)


# รายการสินค้าในใบขอซื้อ (PR Items)
class PRItem(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE,
                                         related_name='items', verbose_name="ใบขอซื้อ")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="อะไหล่")
    quantity = models.IntegerField(verbose_name="จำนวน")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อหน่วย")
    notes = models.TextField(blank=True, verbose_name="หมายเหตุ")

    class Meta:
        verbose_name = "รายการในใบขอซื้อ"
        verbose_name_plural = "รายการในใบขอซื้อ"

    def __str__(self):
        return f"{self.part.name} - {self.quantity} {self.part.unit}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        # อัพเดทราคาต่อหน่วยจากอะไหล่ถ้ายังไม่มีการระบุ
        if self.unit_price == 0 and self.part:
            self.unit_price = self.part.cost

        super().save(*args, **kwargs)

        # อัพเดทยอดรวมในใบขอซื้อ
        if self.purchase_request:
            self.purchase_request.update_total()


# โมเดลสำหรับใบสั่งซื้อ (PO)
class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'แบบร่าง'),
        ('ISSUED', 'ออกใบสั่งซื้อแล้ว'),
        ('PARTIAL', 'รับมอบบางส่วน'),
        ('RECEIVED', 'รับมอบครบแล้ว'),
        ('COMPLETED', 'เสร็จสมบูรณ์'),
        ('CANCELLED', 'ยกเลิก')
    ]

    po_number = models.CharField(max_length=20, unique=True, verbose_name="เลขที่ PO")
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.PROTECT,
                                         related_name='purchase_orders', verbose_name="ใบขอซื้อ")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, verbose_name="ผู้ขาย")

    # ข้อมูลสถานะและวันที่
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="สถานะ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    issued_at = models.DateTimeField(null=True, blank=True, verbose_name="วันที่ออกใบสั่งซื้อ")
    expected_delivery = models.DateField(null=True, blank=True, verbose_name="วันที่คาดว่าจะได้รับ")

    # ข้อมูลการเงิน
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="จำนวนเงินรวม")
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7.0, verbose_name="ภาษีมูลค่าเพิ่ม %")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="จำนวนภาษีมูลค่าเพิ่ม")
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="ยอดรวมทั้งสิ้น")

    # ข้อมูลเพิ่มเติม
    payment_terms = models.CharField(max_length=200, blank=True, verbose_name="เงื่อนไขการชำระเงิน")
    delivery_terms = models.TextField(blank=True, verbose_name="เงื่อนไขการส่งมอบ")
    notes = models.TextField(blank=True, verbose_name="หมายเหตุ")

    # ผู้ดำเนินการ
    created_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                   related_name='created_pos', verbose_name="ผู้สร้าง")
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='approved_pos', null=True, blank=True,
                                    verbose_name="ผู้อนุมัติ")

    class Meta:
        verbose_name = "ใบสั่งซื้อ"
        verbose_name_plural = "ใบสั่งซื้อ"
        permissions = [
            ("issue_po", "Can issue purchase orders"),
            ("receive_po", "Can receive goods for purchase orders"),
        ]

    def __str__(self):
        return f"{self.po_number} - {self.vendor.name}"

    def save(self, *args, **kwargs):
        # สร้างเลขที่ PO อัตโนมัติถ้ายังไม่มี
        if not self.po_number:
            prefix = "PO"
            year = timezone.now().strftime('%y')
            month = timezone.now().strftime('%m')

            # หาเลขลำดับล่าสุดของเดือนนี้
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f"{prefix}{year}{month}"
            ).order_by('-po_number').first()

            if last_po:
                # ตัดเอาเฉพาะเลขลำดับท้าย 4 ตัว
                last_num = int(last_po.po_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1

            # สร้างเลขที่ PO ใหม่
            self.po_number = f"{prefix}{year}{month}{new_num:04d}"

        # คำนวณภาษีและยอดรวม
        self.vat_amount = (self.total_amount * self.vat_percent) / 100
        self.grand_total = self.total_amount + self.vat_amount

        super().save(*args, **kwargs)

    def update_total(self):
        total = sum(item.total_price for item in self.items.all())
        if self.total_amount != total:
            self.total_amount = total
            # คำนวณภาษีและยอดรวมใหม่
            self.vat_amount = (self.total_amount * self.vat_percent) / 100
            self.grand_total = self.total_amount + self.vat_amount
            # ใช้ update เพื่อไม่ให้เรียก save อีกรอบ
            PurchaseOrder.objects.filter(id=self.id).update(
                total_amount=total,
                vat_amount=self.vat_amount,
                grand_total=self.grand_total
            )


# รายการสินค้าในใบสั่งซื้อ (PO Items)
class POItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE,
                                       related_name='items', verbose_name="ใบสั่งซื้อ")
    pr_item = models.ForeignKey(PRItem, on_delete=models.PROTECT, null=True,
                                verbose_name="รายการจากใบขอซื้อ")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="อะไหล่")
    quantity = models.IntegerField(verbose_name="จำนวน")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อหน่วย")

    # ข้อมูลการรับสินค้า
    received_quantity = models.IntegerField(default=0, verbose_name="จำนวนที่รับแล้ว")
    is_fully_received = models.BooleanField(default=False, verbose_name="รับครบแล้ว")

    class Meta:
        verbose_name = "รายการในใบสั่งซื้อ"
        verbose_name_plural = "รายการในใบสั่งซื้อ"

    def __str__(self):
        return f"{self.part.name} - {self.quantity} {self.part.unit}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    @property
    def remaining_quantity(self):
        return self.quantity - self.received_quantity

    def save(self, *args, **kwargs):
        # ตรวจสอบว่ารับสินค้าครบหรือยัง
        if self.received_quantity >= self.quantity:
            self.is_fully_received = True
        else:
            self.is_fully_received = False

        super().save(*args, **kwargs)

        # อัพเดทยอดรวมในใบสั่งซื้อ
        if self.purchase_order:
            self.purchase_order.update_total()


# โมเดลสำหรับการรับสินค้า
class GoodsReceipt(models.Model):
    receipt_number = models.CharField(max_length=20, unique=True, verbose_name="เลขที่ใบรับสินค้า")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT,
                                       related_name='receipts', verbose_name="ใบสั่งซื้อ")
    received_date = models.DateField(default=timezone.now, verbose_name="วันที่รับสินค้า")
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="ผู้รับสินค้า")

    # เอกสารอ้างอิง
    delivery_note = models.CharField(max_length=100, blank=True, verbose_name="เลขที่ใบส่งของ")
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name="เลขที่ใบแจ้งหนี้")

    notes = models.TextField(blank=True, verbose_name="หมายเหตุ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ใบรับสินค้า"
        verbose_name_plural = "ใบรับสินค้า"

    def __str__(self):
        return f"{self.receipt_number} - {self.purchase_order.po_number}"

    def save(self, *args, **kwargs):
        # สร้างเลขที่ใบรับสินค้าอัตโนมัติถ้ายังไม่มี
        if not self.receipt_number:
            prefix = "GR"
            year = timezone.now().strftime('%y')
            month = timezone.now().strftime('%m')

            # หาเลขลำดับล่าสุดของเดือนนี้
            last_receipt = GoodsReceipt.objects.filter(
                receipt_number__startswith=f"{prefix}{year}{month}"
            ).order_by('-receipt_number').first()

            if last_receipt:
                # ตัดเอาเฉพาะเลขลำดับท้าย 4 ตัว
                last_num = int(last_receipt.receipt_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1

            # สร้างเลขที่ใบรับสินค้าใหม่
            self.receipt_number = f"{prefix}{year}{month}{new_num:04d}"

        super().save(*args, **kwargs)


# รายการสินค้าที่รับ
class GoodsReceiptItem(models.Model):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE,
                                      related_name='items', verbose_name="ใบรับสินค้า")
    po_item = models.ForeignKey(POItem, on_delete=models.PROTECT,
                                related_name='receipt_items', verbose_name="รายการในใบสั่งซื้อ")
    quantity = models.IntegerField(verbose_name="จำนวนที่รับ")
    notes = models.TextField(blank=True, verbose_name="หมายเหตุ")

    class Meta:
        verbose_name = "รายการในใบรับสินค้า"
        verbose_name_plural = "รายการในใบรับสินค้า"

    def __str__(self):
        return f"{self.quantity} {self.po_item.part.unit} ของ {self.po_item.part.name}"

    def save(self, *args, **kwargs):
        # เรียก save ปกติก่อน
        super().save(*args, **kwargs)

        # อัพเดทจำนวนที่รับใน PO Item
        po_item = self.po_item
        total_received = sum(item.quantity for item in po_item.receipt_items.all())

        po_item.received_quantity = total_received
        if total_received >= po_item.quantity:
            po_item.is_fully_received = True
        else:
            po_item.is_fully_received = False
        po_item.save()

        # ตรวจสอบและอัพเดทสถานะของ PO
        purchase_order = po_item.purchase_order
        all_items = purchase_order.items.all()

        if all(item.is_fully_received for item in all_items):
            purchase_order.status = 'RECEIVED'
        elif any(item.received_quantity > 0 for item in all_items):
            purchase_order.status = 'PARTIAL'

        purchase_order.save()

        # อัพเดทสต็อกอะไหล่
        part = po_item.part
        part.stock_quantity += self.quantity
        part.save()
