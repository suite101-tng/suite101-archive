import redis
from project import settings
from lib.enums import DEFAULT_PAGE_SIZE
import time
import datetime

''' 
Core Redis classes
'''

#################################################
# REDIS SETUP ###################################
#################################################
class RedisObject(object):
    def __init__(self, redis=None):
        self.init_redis(redis)

    def init_redis(self, redis=None):
        if not redis: 
            self.redis = self.get_redis_connection()
            self.redis_slave = self.get_redis_connection(slave=True)
        else:
            print('we already have a redis object')
            self.redis = redis
            self.redis_slave = redis

    def get_redis_connection(self, slave=False):
        if slave:
            return redis.Redis(host=settings.REDIS_SLAVE_HOST, port=6379, db=0, socket_timeout=5)
        else:
            return redis.Redis(host=settings.REDIS_MASTER_HOST, port=6379, db=0, socket_timeout=5)

    def get_key(self):
        return self.key

    def expire(self, timeout):
        self.redis.expire(self.key, timeout)

    def pipeline(self, transaction=True, shard_hint=None):
        self.pipeline(transaction, shard_hint)

    def execute(self):
        self.execute.pipeline()

        
class List(RedisObject):
    key_format = 'list:%s'

    def __init__(self, object_id, redis=None):
        self.key = self.key_format % object_id
        super(List, self).__init__(redis)

    def add_to_list(self, obj):
        self.redis.lpush(self.key, obj)

    def remove_from_list(self, obj):
        self.redis.lrem(self.key, obj, 0) # we assume we want to remove all occurrences

    def list_length(self):
        return self.redis_slave.llen(self.key)

    def rename(self, new_name):
        self.redis.rename(self.key, new_name)

    def get_random(self):
        return self.redis_slave.srandmember(self.key)

    def get_list(self):
        return self.redis_slave.lrange(self.key, 0, -1)

    def get_member(self, index):
        return self.redis_slave.lindex(self.key, index)

    def trim(self,range_max):
        self.redis.ltrim(self.key, 0, range_max)

    def delete(self):
        return self.redis.delete(self.key)
        
    def get_list_length(self):
        return self.redis.llen()

class RedisHash(RedisObject):
    page_length = DEFAULT_PAGE_SIZE
    key_format = 'hash:%s'

    def __init__(self, object_id, redis=None):
        self.key = self.key_format % object_id
        super(RedisHash, self).__init__(redis)

    def set(self,value=None,hash_id=None):
        if not hash_id:
            hash_id = datetime.date.today()
        if not value:
            value = 1
        self.redis.hset(self.key,hash_id,value)

    def increment(self,increment=None,hash_id=None):
        if not hash_id:
            hash_id = datetime.date.today()
        if not increment:
            increment = 1
        return self.redis.hincrby(self.key,hash_id,increment)

    # Increment by float
    def flincrement(self,increment=None,hash_id=None):
        if not hash_id:
            hash_id = datetime.date.today()
        if not increment:
            increment = 1.0
        return self.redis.hincrbyfloat(self.key,hash_id,increment)
        
    def get(self,hash_id):
        return self.redis_slave.hget(self.key,hash_id)

    def get_values(self):
        return self.redis_slave.hvals(self.key)

    def delete(self,hash_id):
        self.redis.hdel(self.key,hash_id)

    def get_all(self):
        return self.redis_slave.hgetall(self.key)


class SortedSet(RedisObject):
    page_length = DEFAULT_PAGE_SIZE
    key_format = 'sortedset:%s'

    def __init__(self, object_id, redis=None):
        self.key = self.key_format % object_id
        super(SortedSet, self).__init__(redis)

    def add_to_set(self, obj, score=None):
        if not score:
            score = 0
        self.redis.zadd(self.key, obj, score)

    def exists_in_set(self, obj):
        if self.get_member_rank(obj):
            return True
        return False

    def increment(self,value,obj):
        self.redis.zincrby(self.key,value,obj)

    def count_members(self,obj):
        return self.redis.zcard(self.key,obj)

    def get_member_score(self,obj):
        return self.redis.zscore(self.key,obj)

    def get_member_rank(self,obj):
        return self.redis.zrank(self.key,obj)

    def get_set_count(self):
        return self.redis_slave.zcard(self.key)

    def remove_from_set(self, obj):
        return self.redis.zrem(self.key, obj)

    def truncate_set(self, limit):
        self.redis.zremrangebyrank(self.key, 0, -limit)

    def get_set_with_scores(self, page=1):
        start = self.page_length * (page - 1)
        stop = (page * self.page_length) - 1
        redis_results = self.redis_slave.zrevrange(self.key, start, stop, withscores=True)
        print('===== got some results: %s' % redis_results)
        return redis_results
    
    def get_set(self, page=1):
        start = self.page_length * (page - 1)
        stop = (page * self.page_length) - 1
        redis_results = self.redis_slave.zrevrange(self.key, start, stop, withscores=False)
        return redis_results

    def get_set_paged(self, start=0, stop=-1):
        return self.redis_slave.zrevrange(self.key, start, stop, withscores=False)

    def get_next_page_id(self, page):
        get_set = self.get_set(page + 1)
        if get_set:
            return page + 1
        else:
            return None

    def get_prev_page_id(self, page):
        if page <= 1:
            return None
        get_set = self.get_set(page - 1)
        if get_set:
            return page - 1
        else:
            return None

    def delete(self):
        self.redis.delete(self.key)

    def get_latest(self):
        return self.redis_slave.zrevrange(self.key, 0, 0)

    def get(self, obj, number):
        return self.redis_slave.zrange(self.key, number, -1)

    def get_full_set(self, start=0, stop=-1):
        return self.redis_slave.zrevrange(self.key, start, stop)

    def clear_set(self):
        return self.redis.delete(self.key)


class TimeBasedSortedSet(RedisObject):
    page_length = DEFAULT_PAGE_SIZE
    key_format = 'timesortedset:%s'

    def __init__(self, object_id, redis=None):
        self.key = self.key_format % object_id
        super(TimeBasedSortedSet, self).__init__(redis)

    def rename(self, new_name):
        self.redis.rename(self.key, new_name)

    def add_to_set(self, obj, time_score=None):
        if not time_score:
            time_score = time.time()
        self.redis.zadd(self.key, obj, time_score)

    def remove_from_set(self, obj):
        return self.redis.zrem(self.key, obj)

    def truncate_set(self, limit):
        self.redis.zremrangebyrank(self.key, 0, -limit)

    def exists_in_set(self, obj):
        exists = True if self.redis.zscore(self.key,obj) else False
        return exists

    def get_set(self, page=1):
        start = self.page_length * (page - 1)
        stop = (page * self.page_length) - 1
        redis_results = self.redis_slave.zrevrange(self.key, start, stop, withscores=False)
        return redis_results

    def get(self, number):
        return self.redis_slave.zrange(self.key, number, number)

    def get_next_page_id(self, page):
        get_set = self.get_set(page + 1)
        if get_set:
            return page + 1
        else:
            return None

    def get_prev_page_id(self, page):
        if page <= 1:
            return None
        get_set = self.get_set(page - 1)
        if get_set:
            return page - 1
        else:
            return None

    def get_member_rank(self,obj):
        return self.redis.zrank(self.key,obj)

    def trim_set(self,range_max):
        self.redis.zremrangebyscore(self.key, '-inf', range_max)

    def delete(self):
        self.redis.delete(self.key)

    def get_latest(self):
        return self.redis_slave.zrevrange(self.key, 0, 0)

    def get_set_count(self):
        return self.redis.zcard(self.key)

    def get_by_rank(self, rank):
        return self.redis_slave.zrange(self.key, rank, rank)

    def get_full_set(self, withscores=False):
        return self.redis_slave.zrevrange(self.key, 0, -1, withscores)

    def get_set_asc(self, min='-inf', max='+inf', start=None, num=None, withscores=True):     
        return self.redis_slave.zrangebyscore(self.key, min, max, start, num, withscores)

    def get_range_above(self, min, max='+inf', start=None, num=None, withscores=True):
 
        return self.redis_slave.zrangebyscore(self.key, min, max, start, num, withscores)

    def clear_set(self):
        return self.redis.delete(self.key)


class NormalSet(RedisObject):
    key_format = 'normalset:%s'

    def __init__(self, object_id, redis=None):
        self.key = self.key_format % object_id
        super(NormalSet, self).__init__(redis)

    def set_key(self,obj):
        self.redis.set(self.key, obj)

    def add_to_set(self, obj):
        self.redis.sadd(self.key, obj)

    def remove_from_set(self, obj):
        self.redis.srem(self.key, obj)

    def get_random_member(self):
        return self.redis_slave.srandmember(self.key)
        
    def exists_in_set(self, obj):
        return self.redis_slave.sismember(self.key, obj)

    def get_set_count(self):
        return self.redis_slave.scard(self.key)

    def get_full_set(self):
        return self.redis_slave.smembers(self.key)

    def increment(self,increment=None):
        if not increment:
            increment = 1
        return self.redis.incrby(self.key,increment)

    def mget(self):
        return self.redis_slave.mget(self.key)

    def get(self, obj):
        return self.redis_slave.get(self.key, obj)

    def clear(self):
        self.redis.delete(self.key)


'''
Key registry for lib
'''
class TopTags(SortedSet):
    key_format = 'lib:tags:top:%s'
    obj_id = -1

    # key_id = tag filter type
    def __init__(self, key_id, redis=None):
        super(TopTags, self).__init__(key_id, redis)

class PromoConversations(SortedSet):
    key_format = 'lib:promo:stories:discussed'
    obj_id = -1

    def __init__(self, redis=None):
        self.key = self.key_format
        self.init_redis(redis)
