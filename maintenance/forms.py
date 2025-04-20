from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from .models import MaintenanceRequest, Comment, UserProfile, PurchaseRequest, PRItem, RepairEvaluation, PurchaseOrder, \
    POItem, GoodsReceiptItem, GoodsReceipt


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['title', 'category', 'location', 'priority', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'กรอกหัวข้อการแจ้งซ่อม'
            }),
            'category': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2'
            }),
            'location': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ระบุสถานที่'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-3',
                'placeholder': 'รายละเอียดการแจ้งซ่อม'
            }),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'เพิ่มความคิดเห็น...'
            }),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['line_token', 'phone_number', 'notification_preferences']
        widgets = {
            'line_token': forms.TextInput(attrs={'class': 'form-input rounded-lg'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input rounded-lg'}),
            'notification_preferences': forms.Select(attrs={'class': 'form-select rounded-lg'})
        }


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input rounded-lg'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input rounded-lg'}),
            'email': forms.EmailInput(attrs={'class': 'form-input rounded-lg'})
        }


class PurchaseRequestForm(forms.ModelForm):
    ALLOWED_STATUS = ['OUTSOURCED', 'NEED_PARTS', 'TRANSFERRED_PARTS']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        is_edit_mode = self.instance.pk is not None

        # Configure maintenance_request queryset
        if is_edit_mode:
            maintenance_requests = MaintenanceRequest.objects.filter(
                Q(status__in=self.ALLOWED_STATUS) |
                Q(pk=self.instance.maintenance_request.pk)
            )
            # Make maintenance_request readonly in edit mode
            self.fields['maintenance_request'].widget.attrs['disabled'] = True
            self.fields['maintenance_request'].widget.attrs['readonly'] = True
        else:
            maintenance_requests = MaintenanceRequest.objects.filter(
                status__in=self.ALLOWED_STATUS
            )

        self.fields['maintenance_request'].queryset = maintenance_requests

        # Configure evaluation queryset
        if is_edit_mode:
            self.fields['evaluation'].queryset = RepairEvaluation.objects.filter(
                maintenance_request=self.instance.maintenance_request
            )
            # Make evaluation readonly in edit mode
            self.fields['evaluation'].widget.attrs['disabled'] = True
            self.fields['evaluation'].widget.attrs['readonly'] = True
        elif maintenance_requests.first() is not None:
            self.fields['evaluation'].queryset = RepairEvaluation.objects.filter(
                maintenance_request=maintenance_requests.first()
            )
        else:
            self.fields['evaluation'].queryset = RepairEvaluation.objects.none()

    def clean(self):
        """
        Ensure disabled fields are not excluded from cleaned_data
        """
        cleaned_data = super().clean()
        if self.instance.pk:
            cleaned_data['maintenance_request'] = self.instance.maintenance_request
            cleaned_data['evaluation'] = self.instance.evaluation
        return cleaned_data

    class Meta:
        model = PurchaseRequest
        fields = ['title', 'description', 'priority', 'maintenance_request',
                  'evaluation', 'budget_code']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-2 py-2'
            }),
            'maintenance_request': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-2 py-2'
            }),
            'evaluation': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-2 py-2'
            }),
            'budget_code': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
        }


class PRItemForm(forms.ModelForm):
    class Meta:
        model = PRItem
        fields = ['part', 'quantity', 'unit_price', 'notes']
        widgets = {
            'part': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-2 py-2'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
        }


PRItemFormSet = forms.inlineformset_factory(
    PurchaseRequest,
    PRItem,
    form=PRItemForm,
    extra=1,
    can_delete=True
)


class PurchaseOrderForm(forms.ModelForm):
    vat_percent = forms.DecimalField(
        label='VAT %',
        initial=7.00,
        max_digits=5,
        decimal_places=2,
        required=False,
    )

    class Meta:
        model = PurchaseOrder
        fields = ['vendor', 'expected_delivery', 'vat_percent', 'notes']
        widgets = {
            'vendor': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2'
            }),
            'expected_delivery': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'vat_percent': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            })
        }


# forms.py
class POItemForm(forms.ModelForm):
    class Meta:
        model = POItem
        fields = ['pr_item', 'part', 'quantity', 'unit_price']
        widgets = {
            'pr_item': forms.HiddenInput(),  # เปลี่ยนเป็น HiddenInput
            'part': forms.HiddenInput(),  # เปลี่ยนเป็น HiddenInput
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            })
        }


class BasePoItemFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, pr_items=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pr_items = pr_items

        if pr_items:
            self.extra = len(pr_items)
            for i, pr_item in enumerate(pr_items):
                if i < len(self.forms):
                    form = self.forms[i]
                    # Set initial values
                    form.initial = {
                        'pr_item': pr_item.id,
                        'part': pr_item.part.id,
                        'quantity': pr_item.quantity,
                        'unit_price': pr_item.unit_price
                    }
                    # Store PR item for display
                    form.pr_item_object = pr_item


POItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    POItem,
    form=POItemForm,
    formset=BasePoItemFormSet,
    extra=0,  # ตั้งเป็น 0 เพราะจะกำหนดจำนวนตาม pr_items
    can_delete=False
)


class PurchaseOrderIssueForm(forms.ModelForm):
    notes = forms.CharField(
        label='หมายเหตุ',
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'px-3 py-2'}),
        required=False
    )
    confirm_issue = forms.BooleanField(
        label='ยืนยันการออกใบสั่งซื้อ',
        required=True,
        help_text='กรุณาตรวจสอบข้อมูลให้ถูกต้องก่อนยืนยัน'
    )

    class Meta:
        model = PurchaseOrder
        fields = ['payment_terms', 'expected_delivery', 'notes', 'confirm_issue']
        widgets = {
            'expected_delivery': forms.DateInput(attrs={'type': 'date',
                                                        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('confirm_issue'):
            raise forms.ValidationError("กรุณายืนยันการออกใบสั่งซื้อ")
        return cleaned_data


# forms.py
class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ['delivery_note', 'invoice_number', 'received_date', 'notes']
        widgets = {
            'received_date': forms.DateInput(attrs={'type': 'date',
                                                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.po = kwargs.pop('po', None)
        super().__init__(*args, **kwargs)


class GoodsReceiptItemForm(forms.ModelForm):
    class Meta:
        model = GoodsReceiptItem
        fields = ['quantity', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': 0,
            }),
            'notes': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            })
        }


class BaseGoodsReceiptItemFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, po_items=None, **kwargs):
        super().__init__(*args, **kwargs)
        if po_items:
            self.po_items = po_items
            for form, po_item in zip(self.forms, po_items):
                form.po_item = po_item


GoodsReceiptItemFormSet = forms.inlineformset_factory(
    GoodsReceipt,
    GoodsReceiptItem,
    form=GoodsReceiptItemForm,
    formset=BaseGoodsReceiptItemFormSet,
    extra=0,
    can_delete=False
)
