from lib.sets import NormalSet, SortedSet, TimeBasedSortedSet, List
import time

# Link JSON object 
class LinkTeaser(NormalSet):
    key_format = 'linkteaser:%s'

    def __init__(self, link_id, redis=None):
        super(LinkTeaser, self).__init__(link_id, redis)
