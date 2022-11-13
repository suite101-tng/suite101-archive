
from django import forms
from django.contrib.auth import get_user_model

from .models import *

class ProviderImageUploadForm(forms.ModelForm):
    class Meta:
        model = LinkProviderImage
        fields = [
            'image',
        ]