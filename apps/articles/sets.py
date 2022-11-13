from lib.sets import NormalSet, SortedSet, TimeBasedSortedSet, List
import time

'''Redis key registry for stories'''

# Current micro-teaser json for each story
class StoryTeaser(NormalSet):
    key_format = 'story:mini:%s'

    def __init__(self, story_id, redis=None):
        super(StoryTeaser, self).__init__(story_id, redis)

# JsonLD cache
class StoryJsonLd(NormalSet):
    key_format = 'story:jsonld:%s'

    def __init__(self, story_id, redis=None):
        super(StoryJsonLd, self).__init__(story_id, redis)

# User's main story feed (from followers, recommendations, admin pushes)
class UserMainStoryFeed(TimeBasedSortedSet):
    key_format = 'stories:mainstoryfeed:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserMainStoryFeed, self).__init__(user_id, redis)

# Stories the user has read 
class UserReadStories(TimeBasedSortedSet):
    key_format = 'stories:readby:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserReadStories, self).__init__(user_id, redis)
    
# Most discussed stories
class DiscussedStoriesSet(TimeBasedSortedSet):
    key_format = 'stories:discussed'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Recommended stories (featured by mods)
class RecommendedStoriesSet(TimeBasedSortedSet):
    key_format = 'stories:recommended'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Lead story candidates for the homepage splash region
class LeadStoryPool(TimeBasedSortedSet):
    key_format = 'stories:lead'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

############## STORY-SPECIFIC KEYS

# Responses cache
class StoryResponses(SortedSet):
    key_format = 'story:responses:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryResponses, self).__init__(story_id, redis)

# Responses by child response count
class StoryResponsesByResponses(SortedSet):
    key_format = 'story:responses:resps:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryResponsesByResponses, self).__init__(story_id, redis)

class StoryNextRelated(SortedSet):
    key_format = 'story:related:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryNextRelated, self).__init__(story_id, redis)

# Response auths
class StoryResponseAuths(SortedSet):
    key_format = 'story:responses:auths:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryResponseAuths, self).__init__(story_id, redis)

############## TOP LISTS

# UserStats.topstories 
class UserTempTopStories(SortedSet):
    key_format = 'story:temp:top:%s'
    obj_id = -1

    def __init__(self, key_id, redis=None):
        super(UserTempTopStories, self).__init__(key_id, redis)

# Global top stories sets (key_id = #days)
class GlobalMostReadStories(SortedSet):
    key_format = 'story:top:reads:%s'
    obj_id = -1

    def __init__(self, key_id, redis=None):
        super(GlobalMostReadStories, self).__init__(key_id, redis)




