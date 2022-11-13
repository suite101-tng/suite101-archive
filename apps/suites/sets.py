from lib.sets import NormalSet, SortedSet, TimeBasedSortedSet
import time

# Current micro-teaser json for each suite
class SuiteTeaser(NormalSet):
    key_format = 'suite:mini:%s'

    def __init__(self, suite_id, redis=None):
        super(SuiteTeaser, self).__init__(suite_id, redis)

class SuiteActiveHero(NormalSet):
    key_format = 'suite:hero:%s'

    def __init__(self, suite_id, redis=None):
        super(SuiteActiveHero, self).__init__(suite_id, redis)

# Featured Suite members for cover page, etc
class SuiteFeaturedMembers(SortedSet):
    key_format = 'suite:mems:featured:%s'
    obj_id = -1

    def __init__(self, suite_id, redis=None):
        super(SuiteFeaturedMembers, self).__init__(suite_id, redis)

# List of Suites for this member
class UserSuitesSet(SortedSet):
    key_format = 'suites:user:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserSuitesSet, self).__init__(user_id, redis)

#################################################################
#################################################################

# Featured Suites
# populated by lib.utils.get_featured_suites() 
class FeaturedSuiteSet(TimeBasedSortedSet):
    key_format = 'suite:featured'

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)
        
