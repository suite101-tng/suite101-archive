from lib.sets import RedisHash, NormalSet, SortedSet, TimeBasedSortedSet, List

'''
Redis key reigstry for stats
'''

############## STATS PROCESSORS 

# First stop for all stats events
class StatsEventInbox(List):
    key_format = 's:inbox'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Processing index key
class StatsProcessingIndex(NormalSet):
    key_format = 's:processing:index'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

# Events currently being processed
class StatsEventProcessing(List):
    key_format = 's:processing:%s'
    obj_id = -1

    def __init__(self, index, redis=None):
        super(StatsEventProcessing, self).__init__(index, redis)

# Full daily event log (successfully processed)
class StatsFullDailyEventList(List):
    key_format = 's:log:%s'
    obj_id = -1

    def __init__(self, date, redis=None):
        super(StatsFullDailyEventList, self).__init__(date, redis)

# Failed event log
class StatsFailedEventList(List):
    key_format = 's:log:failed'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)     

############## DAILY STATS HASHES

# Daily stats: reads
class UserDailyStatsReads(RedisHash):
    key_format = 's:d:u:reads:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsReads, self).__init__(user_id, redis)

# Daily stats: unique reads
class UserDailyStatsUniques(RedisHash):
    key_format = 's:d:u:uniques:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsUniques, self).__init__(user_id, redis)

# Daily stats: pageviews
class UserDailyStatsPageviews(RedisHash):
    key_format = 's:d:u:pvs:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsPageviews, self).__init__(user_id, redis)

# Daily stats: words_added
class UserDailyStatsWordsAdded(RedisHash):
    key_format = 's:d:u:words:added:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsWordsAdded, self).__init__(user_id, redis)

# Daily stats: words_removed
class UserDailyStatsWordsRemoved(RedisHash):
    key_format = 's:d:u:words:removed:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsWordsRemoved, self).__init__(user_id, redis)

# Daily stats: new posts
class UserDailyStatsPosts(RedisHash):
    key_format = 's:d:u:posts:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsPosts, self).__init__(user_id, redis)

# Daily (global) stats: first posts
class UserDailyStatsFirstPosts(RedisHash):
    key_format = 's:d:u:firstposts:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsFirstPosts, self).__init__(user_id, redis)

# Daily stats: profile views
class UserDailyStatsProfileViews(RedisHash):
    key_format = 's:d:u:profileviews:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsProfileViews, self).__init__(user_id, redis)

# Daily stats: responses
class UserDailyStatsResponses(RedisHash):
    key_format = 's:d:u:resps:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsResponses, self).__init__(user_id, redis)

# Daily stats: user follows (for global stats)
class UserDailyStatsSuiteFollows(RedisHash):
    key_format = 's:d:u:sfols:%s'
    obj_id = -1

    def __init__(self, suite_id, redis=None):
        super(UserDailyStatsSuiteFollows, self).__init__(suite_id, redis)

# Daily stats: suite follows (for global stats)
class UserDailyStatsUserFollows(RedisHash):
    key_format = 's:d:u:ufols:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserDailyStatsUserFollows, self).__init__(user_id, redis)


####################################################
# MONTHLY UNIQUES LISTS 
# List of unique IPs - rolling 30d window 
####################################################

# List of unique IPs (per user)
class UserMonthlyUniques(TimeBasedSortedSet):
    key_format = 's:uniques:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserMonthlyUniques, self).__init__(user_id, redis)


####################################################
# DAILY STORY, SUITE STATS HASHES  
####################################################

# Daily read stats: stories
class StoryDailyStatsReads(RedisHash):
    key_format = 's:d:story:reads:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryDailyStatsReads, self).__init__(story_id, redis)

# Daily read stats: stories
class StoryDailyStatsPageviews(RedisHash):
    key_format = 's:d:story:pvs:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryDailyStatsPageviews, self).__init__(story_id, redis)

# Daily unique read stats: stories
class StoryDailyStatsUniques(RedisHash):
    key_format = 's:d:story:uniques:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryDailyStatsUniques, self).__init__(story_id, redis)

# Daily stats: words_added
class StoryDailyStatsWordsAdded(RedisHash):
    key_format = 's:d:story:w:added:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryDailyStatsWordsAdded, self).__init__(story_id, redis)

# Daily stats: words_removed
class StoryDailyStatsWordsRemoved(RedisHash):
    key_format = 's:d:story:w:removed:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryDailyStatsWordsRemoved, self).__init__(story_id, redis)

# Daily read stats: suites
class SuiteDailyStatsViews(RedisHash):
    key_format = 's:d:suite:views:%s'
    obj_id = -1

    def __init__(self, suite_id, redis=None):
        super(SuiteDailyStatsViews, self).__init__(suite_id, redis)


######################################################
# AGGREGATE STATS FOR USERS, STORIES, SUITES AND CHATS
######################################################

class UserStats(RedisHash):
    key_format = 's:t:u:%s'
    obj_id = -1

    def __init__(self, user_id, redis=None):
        super(UserStats, self).__init__(user_id, redis)

class StoryStats(RedisHash):
    key_format = 's:t:story:%s'
    obj_id = -1

    def __init__(self, story_id, redis=None):
        super(StoryStats, self).__init__(story_id, redis)

class SuiteStats(RedisHash):
    key_format = 's:t:suite:%s'
    obj_id = -1

    def __init__(self, suite_id, redis=None):
        super(SuiteStats, self).__init__(suite_id, redis)

class ChatStats(RedisHash):
    key_format = 's:t:chat:%s'
    obj_id = -1

    def __init__(self, chat_id, redis=None):
        super(ChatStats, self).__init__(chat_id, redis)


####################################################
# ADMIN STATS 
####################################################

########### users

# Count of active users (today)
class UserDailyStatsUsersCount(RedisHash):
    key_format = 's:d:u:glo:all'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis) 

# Count of active users (today)
class UserDailyStatsActiveCount(RedisHash):
    key_format = 's:d:u:glo:active'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)     

# Ratio of active to all users
class UserDailyStatsActiveRatio(RedisHash):
    key_format = 's:d:u:glo:active:ratio'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)     

########### posts

class AdminDailyStatsCounts(RedisHash):
    key_format = 's:d:admin:%s'
    obj_id = -1

    def __init__(self, key_type, redis=None):
        super(AdminDailyStatsCounts, self).__init__(key_type, redis)

########### royalties

####################################################
# UTILITY KEYS 
####################################################

# Daily accounts trimmed
class AdminDailyStatsTrimmedInactive(RedisHash):
    key_format = 's:d:admin:trimmed'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

class AdminTaskMonitor(RedisHash):
    key_format = 's:monitor'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)

class RunTask(RedisHash):
    key_format = 's:runtask'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)