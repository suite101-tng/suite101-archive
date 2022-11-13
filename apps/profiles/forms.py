from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate

from .models import UserImage, UserEmailSettings

class UserCreateForm(forms.ModelForm):
    """
    Model form to create a new user
    """
    name = forms.CharField(max_length=255, required=True)
    # website is a honeypot field!
    website = forms.CharField(required=False)

    class Meta:
        User = get_user_model()
        model = User
        fields = [
            'email',
            'password'
        ]
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserCreateForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = 'Full name'
        self.fields['email'].widget.attrs['placeholder'] = 'Email'
        self.fields['email'].widget.attrs['autocapitalize'] = 'off'
        self.fields['email'].widget.attrs['autocorrect'] = 'off'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'

    def clean_email(self):
        User = get_user_model()
        email = self.cleaned_data["email"]
        try:
            User._default_manager.get(email__iexact=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(
            'That email account is already registered!',
            code='duplicate_username',
        )

    def clean_website(self):
        """ if this field is filled out, it's a bot and we don't let it through """
        if self.cleaned_data['website']:
            raise forms.ValidationError('Invalid form')
        return ''


class UserTwitterRegistrationForm(forms.Form):
    name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'placeholder': 'Name'}))
    email = forms.EmailField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Email'}))
    password = forms.CharField(max_length=128, widget=forms.PasswordInput(attrs={'placeholder': 'Choose a password'}))


class TwitterLinkForm(forms.Form):
    password = forms.CharField(max_length=128, widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'}))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(TwitterLinkForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(TwitterLinkForm, self).clean()
        if not 'password' in cleaned_data:
            raise forms.ValidationError('Please enter a password')
        password = cleaned_data['password']
        self.user_cache = authenticate(email=self.user.email, password=password)
        if self.user_cache is None:
            raise forms.ValidationError('Password does not match')
        return cleaned_data

    def get_user(self):
        return self.user_cache


ERROR_MESSAGE = _("Please enter a correct email and password. ")
ERROR_MESSAGE_RESTRICTED = _("You do not have permission to access the admin.")
ERROR_MESSAGE_INACTIVE = _("This account is inactive.")


class EmailAuthenticationForm(AuthenticationForm):
    """
    Override the default AuthenticationForm to force email-as-username behavior.
    https://github.com/dabapps/django-email-as-username/blob/master/emailusernames/forms.py
    """
    email = forms.EmailField(label=_("Email"), max_length=255)
    message_incorrect_password = ERROR_MESSAGE
    message_inactive = ERROR_MESSAGE_INACTIVE
    
    code_password_error = 'erroremailpassword'
    code_missing_email_error = 'errormissingemail'
    code_missing_password_error = 'errormissingpassword'
    code_missing_everything_error = 'errormissingeverything'

    def __init__(self, request=None, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(request, *args, **kwargs)
        del self.fields['username']
        self.fields['email'].widget.attrs['placeholder'] = 'Email'
        self.fields['email'].widget.attrs['autocapitalize'] = 'off'
        self.fields['email'].widget.attrs['autocorrect'] = 'off'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'
        self.fields.keyOrder = ['email', 'password']

    def clean(self):
        cleaned_data = super(EmailAuthenticationForm, self).clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if not email and not password:
            raise forms.ValidationError(self.code_missing_everything_error)
        elif not email:
            raise forms.ValidationError(self.code_missing_email_error)
        elif not password:
            raise forms.ValidationError(self.code_missing_password_error)
        else:
            self.user_cache = authenticate(email=email, password=password)
            if (self.user_cache is None):
                raise forms.ValidationError(self.code_password_error)
            # if not self.user_cache.is_active:
            #     raise forms.ValidationError(self.message_inactive)
        return cleaned_data

    def get_user(self):
        return self.user_cache


class RequestResetPasswordForm(forms.Form):
    email = forms.EmailField(label=_(""), max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Email'}))

    def clean(self):
        User = get_user_model()
        cleaned_data = super(RequestResetPasswordForm, self).clean()
        email = cleaned_data.get('email')
        if email:
            try:
                self.user_cache = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                raise forms.ValidationError(_('Sorry, we don\'t recognize that email address.'))
        return cleaned_data

    def get_user(self):
        return self.user_cache


class ResetPasswordForm(forms.Form):
    password = forms.CharField(label=_(""), widget=forms.PasswordInput(attrs={'placeholder': 'Choose a new password'}))
    password2 = forms.CharField(label=_(""), widget=forms.PasswordInput(attrs={'placeholder': 'Type it again'}))

    def clean(self):
        cleaned_data = super(ResetPasswordForm, self).clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError(_('Passwords do not match!'))
        return cleaned_data

class ChangeEmailForm(forms.ModelForm):
    email = forms.EmailField(label=_(""), max_length=255)
    class Meta:
        User = get_user_model()
        model = User
        fields = [
            'email'
        ]
    def clean(self):
        User = get_user_model()
        cleaned_data = super(ChangeEmailForm, self).clean()
        email = cleaned_data.get('email')
        if email:
            try:
                User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                pass
            else:
                raise forms.ValidationError(_('That email is already in use, please try again'))
        return cleaned_data

class UserUpdateForm(forms.ModelForm):
    class Meta:
        User = get_user_model()
        model = User
        fields = [
            'first_name',
            'last_name',
            'by_line',
            'personal_url',
            'location'
        ]

        widgets = {
            'by_line': forms.Textarea(attrs={'cols': '', 'rows': '', 'maxlength': '200', 'placeholder': "Type a short byline"}),
            'personal_url': forms.TextInput(attrs={'placeholder': "Link to your personal website"}),
        }

class UserUploadImageForm(forms.ModelForm):
    class Meta:
        model = UserImage
        fields = [
            'image',
        ]

