import re

from django.contrib.auth import get_user_model

SHA1_RE = re.compile('^[a-f0-9]{40}$')

class KeyBasedBackend(object):
    '''
    A simple backend that allows us to log-in a user after they
    click on the activation link to activate thier new profile/account
    After clicking the link and verifying it, we can safely log the user in.
    '''
    def authenticate(self, email=None, key=None, key_type='Reset', **kwargs):
        User = get_user_model()
        '''
        Let's find this user, make sure the key matches and return
        the user and user profile
        '''
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(key):
            try:
                user = User.objects.using('default').get(email__iexact=email)
            except User.DoesNotExist:
                return None

            if key_type == 'Activation':
                if user.activation_key == key:
                    return user
            elif key_type == 'Email':
                if user.email_key == key:
                    return user
            elif key_type == 'PayPalEmail':
                if user.paypal_email_key == key:
                    return user
            else:
                if user.reset_key == key:
                    return user
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.using('default').get(pk=user_id)
        except User.DoesNotExist:
            return None



class EmailBasedBackend(object):
    def authenticate(self, email=None, password=None, **kwargs):
        User = get_user_model()
        if email:
            try:
                user = User.objects.using('default').get(email__iexact=email)
            except User.DoesNotExist:
                return None

            if user.check_password(password):
                return user
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.using('default').get(pk=user_id)
        except User.DoesNotExist:
            return None
