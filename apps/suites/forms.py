
from django import forms
from django.contrib.auth import get_user_model

from .models import *

class SuiteUploadImageForm(forms.ModelForm):
    class Meta:
        model = SuiteImage
        fields = [
            'image',
        ]


class SuiteImageAttrsUpdateForm(forms.ModelForm):
    class Meta:
        model = SuiteImage
        fields = [
            'caption',
            'credit',
            'credit_link',
        ]

class SuiteMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.name

class SuiteCreateForm(forms.ModelForm):
    class Meta:
        model = Suite
        fields = ['name', 'description', 'private']

        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Title'}),
            'description': forms.Textarea(attrs={'cols': '', 'rows': '', 'maxlength': '200', 'placeholder': 'Add a description (optional)'}),
            'private': forms.HiddenInput(),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        name = name.strip()
        if not name:
            raise forms.ValidationError('Please enter a name for your suite!')
        return name

class SuiteInviteForm(forms.ModelForm):
    class Meta:
        model = SuiteInvite
        fields = ['status']


class SuiteRequestForm(forms.ModelForm):
    class Meta:
        model = SuiteRequest
        fields = ['message', 'status']
