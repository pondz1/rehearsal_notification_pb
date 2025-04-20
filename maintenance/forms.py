from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from .models import MaintenanceRequest, Comment, UserProfile, PurchaseRequest, PRItem, RepairEvaluation


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
