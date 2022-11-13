import uuid
import json
import requests
from urllib.request import urlopen
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from social.apps.django_app.views import _do_login

from lib.utils import set_unique_top_level_url
from lib.tasks import new_member
from lib.utils import resize_profile_image

from profiles.models import UserEmailSettings, UserImage


def start_association(*args, **kwargs):
    print('hi, starting association')
    print('kwargs: %s' % kwargs)

def user_details(strategy, details, user=None, *args, **kwargs):
    # import pdb; pdb.set_trace()
    if not user.last_name:
        from social.pipeline.user import user_details as _user_details
        _user_details(strategy, details, user, *args, **kwargs)


def _set_profile_image_from_url(user, image_url):
    r = requests.get(image_url, stream=True)  # Stream in case it's a big file
    if r.status_code == 200:
        img_temp = NamedTemporaryFile(delete=True)
        for chunk in r.iter_content(1024): # Iterate over the streaming data 1024 bytes at a time
            img_temp.write(chunk)
        img_temp.flush()

        filename = '%s.jpg' % uuid.uuid4()
        profile_image = UserImage(user=user)
        profile_image.image.save(filename, File(img_temp))
        profile_image.save()

        resize_profile_image(profile_image)

        user.profile_image = profile_image
        user.save()

def associate_by_email(**kwargs):
    print('----------------------------- associate_by_email')
    User = get_user_model()
    """ if the email of this social auth user matches one of our users, match and associate them """
    print('kwargs details: %s' % kwargs['details'])
    try:
        email = kwargs['details']['email']
        kwargs['user'] = User.objects.get(email__iexact=email)
    except:
        try:
            kwargs['user'] = User.objects.get(email=kwargs['user'].email)
        except:
            pass
    return kwargs

def complete_association(strategy, **kwargs):
    from lib.utils import seems_like_email
    print('trying to complete the association')

    social = kwargs.get('social', False)
    social_user = social.user
    is_new = kwargs.get('is_new', False)
    user = kwargs.get('user', None)
    if not user:
        assert False

    try:
        backend = kwargs['backend']
        provider_name = backend.name
        social = user.social_auth.get(provider=provider_name)
        # social will contain extra_data later.. when asking for extra permissions.. for now we don't need it.
    except Exception as e:
        print(e)
        assert False

    if provider_name == 'facebook':
        if user.facebook_connected:
            return kwargs

        print('this is a new connection (facebook)')
        user.facebook_connected = True
        user.facebook_username = kwargs['details']['username']
        if not user.slug:
            user.slug = set_unique_top_level_url(slugify(user.get_full_name().lower()), user.pk)
        user.save()

        # setup user 1:1 models.
        UserEmailSettings.objects.get_or_create(user=user)

        try:
            url = 'http://graph.facebook.com/%s/picture?type=large&redirect=false' % kwargs['response']['id']
            response = urlopen(url).read()
            json_data = json.loads(response)
            image_url = json_data['data']['url']

            _set_profile_image_from_url(user, image_url)
        except:
            pass


        # grab the facebook url for this user
        try:
            user.facebook_url = kwargs['response']['link']
            user.save()
        except:
            pass

        user.activate_user()
        new_member.delay(user)

    elif provider_name == 'twitter':
        email = kwargs['details']['email']
        user.backend = 'social.backends.twitter.TwitterOAuth'
        if user.twitter_connected:
            user.backend = 'social.backends.twitter.TwitterOAuth'
            login(strategy.request, user)
            return kwargs
        try:
            user.twitter_connected = True
            user.twitter_username = kwargs['details']['username']
            print('email? %s' % seems_like_email(user.email))
        except Exception as e:
            print(e)

        if not user.slug:
            user.slug = set_unique_top_level_url(slugify(user.get_full_name().lower()), user.pk)
        if not seems_like_email(user.email):
            print('this user does not have a real email address...')
            try:
                print('social user: %s' % kwargs['social'].user)
                if seems_like_email('adfs'):
                    user.email = 'asdfs'
            except Exception as e:
                user.email = ''
                print(e)
                pass

        user.save()

        try:
            small_url = kwargs['response']['profile_image_url_https']
            image_url = small_url.replace('normal', '400x400')
            _set_profile_image_from_url(user, image_url)
        except:
            pass
        
        # activate the user
        user.activate_user()
        new_member.delay(user)
        login(strategy.request, user)

    return kwargs


def complete_disconnect(**kwargs):
    user = kwargs.get('user', None)
    if not user or not user.email:
        assert False
    try:
        provider_name = kwargs['backend'].name
    except:
        assert False

    if provider_name == 'facebook':
        user.facebook_connected = False
        user.facebook_url = ''
        user.save()
    elif provider_name == 'twitter':
        user.twitter_connected = False
        user.twitter_username = ''
        user.save()

    return kwargs


from django.shortcuts import redirect
from social.pipeline.partial import partial

# @partial
# def require_email_password(strategy, details, user=None, is_new=False, *args, **kwargs):
#     # import pdb; pdb.set_trace()
#     print 'requiring email password; strategy: %s' % strategy
#     print 'backend: %s' % kwargs['backend']
#     print 'name? %s' % kwargs['backend'].name
#     print 'is_new? %s' % is_new

#     try:
#         provider_name = kwargs['backend'].name
#     except:
#         return kwargs

#     if is_new and provider_name == 'twitter':
#         try:
#             user.first_name = kwargs['response']['name'].split(' ')[0]
#             user.last_name = ' '.join(kwargs['response']['name'].split(' ')[1:])
#             user.save()
#         except Exception as e:
#             print(e)
#             pass

#     user.backend = 'django.contrib.auth.backends.ModelBackend'
#     login(strategy.request, user)
#     return redirect('profile_twitter_create')

#     print 'not sure what to do here...'


