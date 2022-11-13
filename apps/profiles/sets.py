from lib.sets import NormalSet, TimeBasedSortedSet, SortedSet, RedisHash
import time

# Current micro-teaser json for each user
class UserTeaser(NormalSet):
    key_format = 'userteaser:%s'

    def __init__(self, user_id, redis=None):
        super(UserTeaser, self).__init__(user_id, redis)

# User's followers
class UserFollowersSet(TimeBasedSortedSet):
    key_format = 'users:userfollowers:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserFollowersSet, self).__init__(user_id, redis)

# Users who will allow anybody to get in touch
class AnybodiesSet(SortedSet):
    key_format = 'users:anybodies'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Mutual follows set
class MutualFollowsSet(TimeBasedSortedSet):
    key_format = 'users:mutfols:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(MutualFollowsSet, self).__init__(user_id, redis)

# Users this user is following
class UserFollowsUsersSet(TimeBasedSortedSet):
    key_format = 'users:userfollowsusers:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserFollowsUsersSet, self).__init__(user_id, redis)

# Suites this user is following
class UserFollowsSuitesSet(TimeBasedSortedSet):
    key_format = 'users:userfollowssuites:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserFollowsSuitesSet, self).__init__(user_id, redis)

# Current micro-teaser json for each user
class UserTeaser(NormalSet):
    key_format = 'userteaser:%s'

    def __init__(self, user_id, redis=None):
        super(UserTeaser, self).__init__(user_id, redis)
 
# User's current active suite (we expire this after 5 min)
class UserActiveSuite(NormalSet):
    key_format = 'activesuite:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserActiveSuite, self).__init__(user_id, redis)

# Featured members
class FeaturedMemberSet(TimeBasedSortedSet):
    key_format = 'users:featured'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Featured members
class FailedDecodesSet(RedisHash):
    key_format = 'log:decodes'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

###################################
# utility keys
###################################

class UserSeesWelcomeTour(NormalSet):
    key_format = 'users:welcome'

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# to throttle anonymous searches we count recent searches made from IP
class AnonymousParentSearchThrottle(NormalSet): 
    key_format = 'anon:parentsearches:%s'

    def __init__(self, ip_address, redis=None):
        super(AnonymousParentSearchThrottle, self).__init__(ip_address, redis)

        