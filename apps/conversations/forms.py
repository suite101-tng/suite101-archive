from django import forms

from .models import Post
from lib.models import GenericImage
from suites.forms import SuiteMultipleChoiceField

class PostUploadImageForm(forms.ModelForm):
    class Meta:
        model = GenericImage
        fields = [
            'image'
        ]
