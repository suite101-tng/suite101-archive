from lib.sets import RedisObject, SortedSet, TimeBasedSortedSet, NormalSet
import time

class ConversationMembers(SortedSet):
    key_format = 'conv:members:%s'

    def __init__(self, conv_id, redis=None):
        super(ConversationMembers, self).__init__(conv_id, redis)

# Micro-teaser json for each chat
class ConvTeaser(NormalSet):
    key_format = 'conv:mini:%s'

    def __init__(self, conv_id, redis=None):
        super(ConvTeaser, self).__init__(conv_id, redis)

# Micro-teaser json for each chat
class PostTeaser(NormalSet):
    key_format = 'post:mini:%s'

    def __init__(self, post_id, redis=None):
        super(PostTeaser, self).__init__(post_id, redis)

class UserUnreadConvSet(SortedSet): # score with [number of unread msgs]
    key_format = 'conv:unread:%s'

    def __init__(self, user_id, redis=None):
        super(UserUnreadConvSet, self).__init__(user_id, redis)

# class UserChatNotifySet(TimeBasedSortedSet):
#     key_format = 'user:chat:notify:%s'

#     def __init__(self, user_id, redis=None):
#         super(UserChatNotifySet, self).__init__(user_id, redis)
