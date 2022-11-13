from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from articles.models import Article
from suites.models import Suite
from links.models import Link

def unread_in_chat(chat_pk, user_pk):
    from chat.sets import UserUnreadChatSet
    try:
        return UserUnreadChatSet(user_pk).get_member_score(chat_pk)
    except:
        return None

def send_chat_invite_notification(user, invite, chat, email, message):
    from lib.tasks import send_email
    emails = [email, ]

    register_url = '%s?auth=%s' % (reverse('register'), invite.get_auth_key())
    chat_url = '%s&auth=%s' % (chat.get_absolute_url(), invite.get_auth_key())
    context = {
        'chat_url': '%s%s' % (settings.SITE_URL, chat_url),
        'register_url': '%s%s' % (settings.SITE_URL, register_url),
        # 'object': chat.content_object,
        # 'author': chat.content_object.author,
        'inviter': user.get_full_name(),
        'message': message,
    }
    title = '%s has invited you to a discussion on Suite' % (user.get_full_name())
    send_email.delay(emails, title, 'emails/chat_invite_notification', context)

def send_unread_chat_notification(user, chat_member, chat):
    import celery
    from lib.tasks import send_email
    from datetime import datetime, timedelta
    now = datetime.now()
    eta = now + timedelta(seconds=1800)#30 minutes
    countdown = 5 #5 seconds
    # eta = now + timedelta(seconds=300)#5 minutes
    # countdown = 300 #5 minutes
    unread_count = 1

    
    if chat_member.unread_celery_task_id and chat_member.unread_task_eta_datetime and chat_member.unread_task_eta_datetime > now:
        # if there's a task for previous unread msgs already and it hasn't fired
        # kill that task and start a new one with the same eta
        celery.task.control.revoke(chat_member.unread_celery_task_id)
        eta = chat_member.unread_task_eta_datetime
        delta = eta - now # time let until eta
        countdown = int(delta.total_seconds()) # time left until eta in INT seconds
        unread_count = chat_member.unread_chat_messages_count + 1
    elif chat_member.unread_task_eta_datetime and chat_member.unread_task_eta_datetime < now:
        # we've already sent an alert to this user about unread msgs on this thread.
        # figure out if it was less than 24 hours ago, if it was, do nothin, else proceed
        if chat_member.unread_task_eta_datetime + timedelta(hours=23, minutes=30) > now:
            return
    chat_member.unread_chat_messages_count = unread_count
    emails = [user.email,]
    template_name = 'emails/chat_unread_messages'
    # if user == chat.content_object.author:
        # template_name = 'somethingelse'
    context = {
        'user': user,
        'message_count': unread_count,
        'chat': chat,
    }
    title = 'You have unread messages'
    result = send_email.apply_async(args=[emails, title, template_name, context], countdown=countdown)
    chat_member.unread_celery_task_id = result.task_id
    chat_member.unread_task_eta_datetime = eta
    chat_member.save()
    # send_email(emails, title, 'emails/chat_unread_messages', context)





