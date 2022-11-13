from chat.sets import UserUnreadChatSet

def unread_chats(request):

    if request.user.is_authenticated():
        unread_chats = UserUnreadChatSet(request.user.pk).get_set_count()
        return {
        'unread_chats': unread_chats if unread_chats > 0 else None
        }
    return {'unread_chats': 25}
