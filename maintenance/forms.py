from django import forms
from django.contrib.auth.models import User

from .models import MaintenanceRequest, Comment, UserProfile


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
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'location': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ระบุสถานที่'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
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
