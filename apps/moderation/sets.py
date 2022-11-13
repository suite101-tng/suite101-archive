from lib.sets import NormalSet

# Admin user is hijacking a user account
class AdminHijackKey(NormalSet):
    key_format = 'admin:hijack:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(AdminHijackKey, self).__init__(user_id, redis)

