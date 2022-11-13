import json
import time, datetime
# import struct
import gc
# import base64
import base32_crockford
import uuid
import requests, json, urllib
from urllib.request import urlopen
from urllib.parse import urlparse
from PIL import Image, ImageFilter
from io import StringIO
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.urlresolvers import reverse
from django.db.models import Q   
from lib.cache import get_object_from_pk, get_object_from_hash   

from lib.enums import *
# from zbase32 import *
from project import settings

def get_object_from_input(request, input_string):
    from links.models import Link, LinkProvider
    '''user submits a link (or something); we try to return an object'''
    user = request.user

    if 'localhost' in settings.SITE_URL:
        find_suite = 'localhost'
    else:
        find_suite = 'suite.io'

    fetched_object = created = provider = None

    # try to get model object from hash
    if find_suite in input_string or input_string[0] == '/':  
        try:
            slug = urlparse(input_string).path
            last_part = slug.rsplit('/',1)[1]
            fetched_object = get_object_from_hash(last_part, False)                
        except Exception as e:
            pass
            
    # try to get a pre-existing Link object
    else:
        try:
            fetched_object = Link.objects.get(Q(link__icontains=input_string))
        except Exception as e:
            pass

    if not fetched_object:
        try:
            fresh_oembed_data, normalized_url, media_type = fetch_oembed_data(input_string)
            if not fresh_oembed_data:
                return None
            oembed_string = json.dumps(fresh_oembed_data)

            try:
                provider_url = fresh_oembed_data['provider_url']
            except Exception as e:
                try:
                    provider_url = slug.rsplit('/',1)[0]
                except Exception as e:
                    provider_url = ''

            try:
                provider, provider_created = LinkProvider.objects.get_or_create(link=provider_url)
            except Exception as e:
                provider_created = False

            if provider_created:
                try:
                    provider_name = fresh_oembed_data['provider_name']
                except Exception as e:
                    provider_name = ''

                provider.name = provider_name
                provider.link = provider_url
                try:
                    provider.image = process_provider_image(provider, fresh_oembed_data)
                except Exception as e:
                    pass

                provider.save()

            if not provider:
                return None

            try:
                fetched_object, link_created = Link.objects.get_or_create(link=normalized_url, provider=provider)
                if link_created:
                    fetched_object.provider = provider
                    fetched_object.oembed_string = oembed_string
                    fetched_object.media_type = media_type
            except Exception as e:
                pass
                
            if created:
               fetched_object.added_by = user
            fetched_object.save()
            fetched_object.invalidate()


        except Exception as e:
            pass

    return fetched_object

def fetch_oembed_data(url_string):
    from links.models import Link
    from links.sets import LinkTeaser
    import twitter
    import re

    embedly_key = settings.EMBEDLY_KEY
    consumer_key = settings.TWITTER_KEY
    consumer_secret = settings.TWITTER_SECRET
    access_token = settings.TWITTER_ACCESS_TOKEN
    access_token_secret = settings.TWITTER_ACCESS_TOKEN_SECRET

    twitter_api = twitter.Api(consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token_key=access_token,
        access_token_secret=access_token_secret)

    find_tweet = '<blockquote class="twitter-tweet"'
    find_twitter_status = 'twitter.com'
    find_soundcloud = 'soundcloud.com'
    find_instagram = 'instagram.com'
    find_instagram_short = 'instagr.am'
    find_other_media = ['rich', 'video', 'audio']

    oembed_data = None
    normalized_url = None
    media_type = 'unknown'

    def encoded_dict(in_dict):
        out_dict = {}
        for k, v in in_dict.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif isinstance(v, str):
                # Must be encoded in UTF-8
                v.decode('utf8')
            out_dict[k] = v
        return out_dict

    # first, try some known oembed endpoints
    if find_tweet in url_string:
        twitter_widget_script = '<script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>'
        cleansed_tweet = url_string.replace(twitter_widget_script,"")
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url_string)
        tweet_url = urls[-1]
        tweet_id = int(tweet_url.split("/status/",1)[1])

        oembed_data = twitter_api.GetStatusOembed(tweet_id, omit_script=True)
        normalized_url = tweet['url']
        media_type = 'tweet'
        
    elif find_twitter_status in url_string:
        print('get the id from the twitter status link...')

    elif find_soundcloud in url_string:
        try:
            options = {'url': url_string, 'format': 'json'}
            encoded_options = urllib.urlencode(encoded_dict(options))
            soundcloud_url = 'http://soundcloud.com/oembed?%s' % encoded_options

            embed = requests.get(soundcloud_url)
            oembed_data = embed.json()
            normalized_url = url_string
            media_type = 'audio'

        except Exception as e:
            print('did not get anything from soundcloud: %s' % e)

    elif find_instagram in url_string or find_instagram_short in url_string:
        try:
            options = {'url': url_string, 'format': 'json', 'omitscript': 'true'}
            encoded_options = urllib.urlencode(encoded_dict(options))
            instagram_url = 'https://api.instagram.com/oembed?%s' % encoded_options
            embed = requests.get(instagram_url)
            oembed_data = embed.json()
            # note: instagram returns 'thumbnail_url'; we care about the embed url
            normalized_url = url_string
            media_type = 'instagram'

        except Exception as e:
            print('did not get anything from instagram: %s' % e)

    if not oembed_data:
        try:        
            options = {'key': embedly_key, 'url': url_string, 'format': 'json'}
            encoded_options = urllib.urlencode(encoded_dict(options))
            embedly_url = 'http://api.embed.ly/1/extract?%s' % encoded_options
            embedly_fetch = requests.get(embedly_url)
            oembed_data = embedly_fetch.json()
            normalized_url = oembed_data['url']
            try:
                media_type = oembed_data['media']['type']
            except:
                try:
                    media_type = oembed_data['type']
                except: 
                    pass
            
        except Exception as e:
            print('problem fetching oembed string from embedly: %s' % e)

    return oembed_data, normalized_url, media_type

def process_provider_image(provider, oembed_string):
    ''' try to fetch and build a provider icon from a link's oembed string '''
    import cStringIO
    from django.core.files.base import ContentFile
    from lib.utils import download_image_from_url, valid_img     
    from links.models import LinkProviderImage

    try:
        icon_url = oembed_string['favicon_url']
    except Exception as e:
        return

    if icon_url:
        icon = download_image_from_url(icon_url)

        from django.core.files.base import ContentFile
        from lib.utils import download_image_from_url, valid_img
        import cStringIO
        try:
            image = download_image_from_url(icon_url)
        except:
            image = None

        if image:
            try:
                provider_image, created = LinkProviderImage.objects.get_or_create(provider=provider)
                filename = provider_image.provider_image_filename()
                provider_image.image = filename
                tempfile = image
                tempfile_io = cStringIO.StringIO() # file-like object in memory that you can then save
                tempfile.save(tempfile_io, format='png')
                provider_image.image.save(filename, ContentFile(tempfile_io.getvalue()), save=True)
                provider.image = provider_image
            except Exception as e:
                print('failed to process provider icon: %s' % e)
                provider.image = ''
            provider.save()
            return provider.image
    return None

