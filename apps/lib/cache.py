from django.http import Http404
from lib.enums import *
from project import settings
from lib.sets import RedisObject
CACHE_NAME = 'default'

def get_object_from_slug(model, slug, raise404=True, *related):
    import pickle
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()    
    slug = slug.lower()
    obj = None
    try:
        obj_cache_key = model.CacheKey.obj_cache_key + ':%s' % slug 
        model_str = redis.get(obj_cache_key)
        if model_str:
            obj = pickle.loads(model_str)
    except Exception as e:
        pass

    if not obj:    
        try:
            if related:
                obj = model.objects.select_related(*related).get(slug__exact=slug)
            else:
                obj = model.objects.get(slug__exact=slug)
        except model.DoesNotExist:
            if raise404:
                raise Http404
            else:
                return None
        try:
            pickled = pickle.dumps(obj)
            pipe.set(obj_cache_key,pickled)
            pipe.expire(obj_cache_key, settings.DEFAULT_CACHE_TIMEOUT)
            pipe.execute()
        except Exception as e:
            pass

    return obj

def get_object_from_hash(hashed_id, raise404=True):
    from lib.utils import decode_hashed_id
    from conversations.models import Conversation, Post
    from suites.models import Suite
    from links.models import Link
    obj = None
    stripped_hashed_id = hashed_id.strip()

    try:
        object_type, object_id = decode_hashed_id(stripped_hashed_id)
    except:
        if raise404:
            raise Http404
        else:
            return None

    if object_type == HASH_TYPE_STORY: # try to redirect to matching conversation
        obj = Conversation.objects.select_related('owner').get(archive_pk=object_id)
    elif object_type == HASH_TYPE_SUITE:
        obj = get_object_from_pk(Suite, object_id, raise404, 'owner', 'owner__profile_image', 'hero_image')
    elif object_type == HASH_TYPE_CONVERSATION:
        obj = get_object_from_pk(Conversation, object_id, raise404)
    elif object_type == HASH_TYPE_POST:
        obj = get_object_from_pk(Post, object_id, raise404, 'conversation')        
    elif object_type == HASH_TYPE_LINK:
        obj = get_object_from_pk(Link, object_id, raise404)

    if obj and str(obj.hashed_id) == str(stripped_hashed_id):
        return obj

    if raise404:
        raise Http404

    return None

def get_object_from_pk(model, pk, raise404=True, *related):
    import pickle
    redis = RedisObject().get_redis_connection()
    pipe = redis.pipeline()
    model_str = None
    obj = None
    try:
        obj_cache_key = model.CacheKey.obj_cache_key + ':%s' % pk 
        model_str = redis.get(obj_cache_key)
        if model_str:
            obj = pickle.loads(model_str)
    except:
        pass

    if not obj:    
        try:
            if related:
                obj = model.objects.select_related(*related).get(pk=pk)
            else:
                obj = model.objects.get(pk=pk)
        except:
            return None
        try:
            pickled = pickle.dumps(obj)
            pipe.set(obj_cache_key,pickled)
            pipe.expire(obj_cache_key, settings.DEFAULT_CACHE_TIMEOUT)
            pipe.execute()
        except:
            pass
    return obj    

def invalidate_object(model_object):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from articles.sets import StoryTeaser
    from articles.models import Article, StoryParent, ArticleImage
    from lib.models import Follow
    from support.models import SupportQuestion
    from links.models import Link, LinkProvider
    from conversations.models import Conversation
    from notifications.models import Notification
    from suites.models import Suite, SuiteImage, SuitePost

    redis = RedisObject().get_redis_connection(slave=False)
    pipe = redis.pipeline()
    User = get_user_model()
    content_type = ContentType.objects.get_for_model(model_object)

    def invalidate_story(pk):
        pipe.delete('story:mini:%s' % pk)
        pipe.delete('story:obj:%s' % pk)
        pipe.delete('story:full:%s' % pk)
        pipe.delete('story:responses:%s' % pk)
        pipe.delete('story:responses:resps:%s' % pk)
        pipe.delete('story:jsonld:%s' % pk)

    if content_type == ContentType.objects.get_for_model(Article):
        invalidate_story(model_object.pk)
        children = model_object.get_response_pks()
        if children:
            for child_pk in children:
                pipe.delete('story:mini:%s' % child_pk)

        # invalidate notifications that reference this object
        notif_pks = Notification.objects.filter(object_id=model_object.pk, content_type=content_type).values_list('pk', flat=True)
        if notif_pks:
            for pk in notif_pks:
                pipe.delete('notif:full:%s' % pk)

    elif content_type == ContentType.objects.get_for_model(User):
        pipe.delete('user:mini:%s' % model_object.pk)
        pipe.delete('user:obj:%s' % model_object.pk)
        pipe.delete('user:obj:%s' % model_object.slug)
        pipe.delete('user:full:%s' % model_object.pk)
        story_pks = Article.objects.filter(author=model_object).values_list('pk', flat=True)
        if story_pks:
            for pk in story_pks:
                invalidate_story(pk)
    elif content_type == ContentType.objects.get_for_model(SupportQuestion):
        pipe.delete('support:mini:%s' % model_object.pk)        
    elif content_type == ContentType.objects.get_for_model(LinkProvider):
        pipe.delete('provider:mini:%s' % model_object.pk)
        links_from_provider = Link.objects.filter(provider=model_object).values_list('pk', flat=True)
        if links_from_provider:
            for link in links_from_provider:
                pipe.delete('link:obj:%s' % link)
                pipe.delete('link:mini:%s' % link)
                pipe.delete('link:full:%s' % link)

    elif content_type == ContentType.objects.get_for_model(SuitePost):
        pipe.delete('suite:post:%s' % model_object.pk)
        pipe.delete('suite:posts:%s' % model_object.suite.pk)

    elif content_type == ContentType.objects.get_for_model(Suite):
        pipe.delete('suite:mini:%s' % model_object.pk)
        pipe.delete('suite:obj:%s' % model_object.pk)
        pipe.delete('suite:full:%s' % model_object.pk)
        pipe.delete('suite:hero:%s' % model_object.pk)     
        pipe.delete('s:t:suite:%s' % model_object.pk)     
        pipe.delete('suite:posts:%s' % model_object.pk)     

    elif content_type == ContentType.objects.get_for_model(Conversation):
        pipe.delete('conv:mini:%s' % model_object.pk)
        pipe.delete('conv:obj:%s' % model_object.pk)
        pipe.delete('conv:full:%s' % model_object.pk)
        pipe.delete('conv:members:%s' % model_object.pk)

    elif content_type == ContentType.objects.get_for_model(Follow):
        # get follower (user)
        # invalidate user
        # clear user.followed_stuff set
        # get followed_object
        # invalidate_object
        # clear followed_object.followers set
        print('invalidating a Follow')

    elif content_type == ContentType.objects.get_for_model(ArticleImage):
        pipe.delete('story:img:%s' % model_object.pk)
        
    elif content_type == ContentType.objects.get_for_model(SuiteImage):
        pipe.delete('suite:hero:%s' % model_object.suite.pk)
        pipe.delete('suite:img:%s' % model_object.pk)
        
    pipe.execute()     
