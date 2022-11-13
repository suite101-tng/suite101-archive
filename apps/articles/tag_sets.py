from lib.sets import SortedSet, NormalSet
from lib.enums import DEFAULT_PAGE_SIZE


class AutocompleteSet(SortedSet):
    ''' Autocomplete Set based on http://oldblog.antirez.com/post/autocomplete-with-redis.html
        and this python port https://gist.github.com/varunpant/2624605 '''
    key_format = 't:autocompete'

    def __init__(self, redis=None):
        self.key = self.key_format
        super(SortedSet, self).__init__(redis)

    def add_text_to_set(self, text):
        # replace any dashes with actual spaces, strip any leading/trailing spaces
        n = text.strip().replace('-', ' ')

        # if the text already exists.. don't bother
        if self.exists_in_set(n):
            return

        # enter each varation of the word starting with the first letter
        for l in range(1,len(n) + 1):
            prefix = n[0:l]
            self.add_to_set(prefix)

        # finally, add the entire word plus the * to mark the end of the word.
        self.add_to_set(n+'*')

    def autocomplete(self, text_query, count=DEFAULT_PAGE_SIZE):
        # import pdb; pdb.set_trace()
        results = []
        rangelen = 50 # This is not random, try to get replies < MTU size
        start = self.get_member_rank(text_query)
        if not start:
             return []
        while (len(results) != count):
            range = self.redis_slave.zrange(self.key, start, start+rangelen-1)
            start += rangelen
            if not range or len(range) == 0:
                break
            for entry in range:
                minlen = min(len(entry),len(text_query))             
                if entry[0:minlen] != text_query[0:minlen]:                
                    count = len(results)
                    break              
                if entry[-1] == "*" and len(results) != count:                 
                    results.append(entry[0:-1])
         
        return results


class AllTagSet(AutocompleteSet):
    key_format = 't:all'

class TagStorySet(SortedSet):
    key_format = 't:stories:%s'


# class TagStorySet(NormalSet):
#     ''' A normal redis set (non-sorted) to keep track of stories that have a specific tag.
#         The assumption is that sorting will be done elsewhere '''
#     page_length = DEFAULT_PAGE_SIZE
#     # tag is the key variable (dashes, not spaces)
#     key_format = 't:stories:%s'

#     def add_story(self, story):
#         # key = spaceless tags
#         key = "".join(self.key.split())
#         self.redis.sadd(key, story)

#     def get_stories(self):
#         print 'self? %s' % self
#         print 'self.key: %s' % self.key
#         key = "".join(self.key.split())
#         print 'key: %s' % key
#         test = self.redis_slave.smembers(key)
#         print '------ test is: %s' % test
#         return test

#     def get_popular_stories(self, page=1):
#         from articles.sets import TopStories7d
#         # grab the most popular stories using this tag
#         # ex. TagStorySet('basketball-court').get_popular_stories()

#         # start with updating an intersection
#         # this set contains pks of stories that have this tag
#         # the 7 day weighted set contains pks of stories sorted by 7day reads.
#         keys = [self.key, TopStories7d().key]
#         self.redis_slave.zinterstore('tmp:%s' % self.key, keys, aggregate='max')

#         start = self.page_length * (page - 1)
#         stop = (page * self.page_length) - 1
#         story_pks = self.redis_slave.zrevrange('tmp:%s' % self.key, start, stop, withscores=False)
#         # could return story objects.. but we won't
#         # in case we want to ... this should work.   Article.objects.filter(pk__in=story_pks)
#         return story_pks


class StoryWeightedSet(SortedSet):
    key_format = 'story:weighted:set'

    def __init__(self, redis=None):
        self.key = self.key_format
        super(SortedSet, self).__init__(redis)

    def add_story(self, story, score):
        # this is an extra, unnecessary layer now.. but later we might want to 
        # add more than just the story pk, so we'll pass in the entire story obj
        # and just pull out the pk for now.
        self.add_to_set(story.pk, score)


class StoryWeighted7DaySet(StoryWeightedSet):
    key_format = 'story:weighted:7day:set'

    # for 7 day, example usage
    # StoryWeighted7DaySet().add_story(story, story.stats.reads_7d)



