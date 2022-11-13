from django import forms
from .models import Flag, RoyalApplication

class FlagCreateForm(forms.ModelForm):
    class Meta:
        model = Flag
        fields = ['message', 'reason']

    def __init__(self, *args, **kwargs):
        super(FlagCreateForm, self).__init__(*args, **kwargs)
        self.fields['message'].widget.attrs['placeholder'] = 'Optional message'


class FlagUserForm(FlagCreateForm):
    FLAG_CHOICES = (
        ('Offensive', 'I find this person offensive'),
        ('Identity', 'Not a real person'),
        ('Spam', 'This person is posting spam'),
        ('Other', 'Other'),
    )
    reason = forms.ChoiceField(choices=FLAG_CHOICES)


class FlagArticleForm(FlagCreateForm):
    FLAG_CHOICES = (
        ('Offensive', 'I find it offensive'),
        ('Editorial', 'Factual or editorial issues'),
        ('Copyright', 'Copyright infringement'),
        ('Spam', 'Spam: product or service promo'),
        ('Other', 'Other'),
    )
    reason = forms.ChoiceField(choices=FLAG_CHOICES)

class FlagChatForm(FlagCreateForm):
    FLAG_CHOICES = (
        ('Offensive', 'This message is offensive'),
        ('Attack', 'This message is an attack'),
        ('Other', 'Other'),
    )
    reason = forms.ChoiceField(choices=FLAG_CHOICES)

class FlagSuiteForm(FlagCreateForm):
    FLAG_CHOICES = (
        ('Offensive', 'I find it offensive'),
        ('Editorial', 'Factual or editorial issues'),
        ('Copyright', 'Copyright infringement '),
        ('Spam', 'Spam: product or service promo'),
        ('Other', 'Other'),
    )
    reason = forms.ChoiceField(choices=FLAG_CHOICES)





