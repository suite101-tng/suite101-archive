from django import forms

from .models import Article, ArticleImage
from suites.forms import SuiteMultipleChoiceField


class ArticleCreateForm(forms.ModelForm):
    publish = forms.BooleanField(required=False)
    title = forms.CharField(widget=forms.Textarea(attrs={"cols":"", "rows": ""}), required=False)

    class Meta:
        model = Article
        fields = ['title', 'subtitle', 'body', 'publish']

    def __init__(self, *args, **kwargs):
        super(ArticleCreateForm, self).__init__(*args, **kwargs)
        self.fields['body'].widget.attrs['cols'] = ''
        self.fields['body'].widget.attrs['rows'] = ''
        self.fields['title'].widget.attrs['placeholder'] = 'Give your story a name'
        self.fields['subtitle'].widget.attrs['cols'] = ''
        self.fields['subtitle'].widget.attrs['rows'] = ''
        self.fields['subtitle'].widget.attrs['placeholder'] = 'Add an optional intro'
        if self.instance.status == Article.STATUS.published:
            self.fields['publish'].widget.attrs['checked'] = 'checked'

    def clean_title(self):
        title = self.cleaned_data['title']
        title = title.strip()
        return title


class ArticleUploadImageForm(forms.ModelForm):
    class Meta:
        model = ArticleImage
        fields = [
            'image',
            'is_main_image'
        ]

class ArticleImageAttrsUpdateForm(forms.ModelForm):
    class Meta:
        model = ArticleImage
        fields = [
            'is_main_image',
            'caption',
            'credit',
            'credit_link',
        ]
        widgets = {
            'is_main_image': forms.HiddenInput(),
        }
