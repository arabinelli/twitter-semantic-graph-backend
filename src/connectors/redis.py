import functools, pickle, os, zlib
import redis

from datetime import timedelta
from redis import Redis

REDIS_URL = os.environ.get("REDIS_URL")


class RedisClient:
    def __init__(self, hostname=REDIS_URL, port=6379, db=0, password=None):
        if "redis://" in hostname:
            self.r = redis.from_url(REDIS_URL)
        else:
            self.r = Redis(host=hostname, port=port, db=db, password=password)

    def cache(self, func, expiration_time=timedelta(hours=8)):
        """Redis cache wrapper

        Args:
            time (datetime.timedelta, optional): [description]. Defaults to timedelta(hours=8).
        """
        functools.wraps(func)

        def wrapper(*args, **kwargs):
            cache_hash = self.create_hash("cache", func, args, kwargs)
            existing_cache = self.r.get(cache_hash)
            if existing_cache is not None:
                print("Returning result from the cache")
                return pickle.loads(zlib.decompress(existing_cache))
            else:
                result = func(*args, **kwargs)
                try:
                    self.r.setex(
                        cache_hash,
                        time=expiration_time,
                        value=zlib.compress(pickle.dumps(result)),
                    )
                    print("Result saved in the cache")
                except redis.exceptions.ResponseError as e:
                    print(e)
                return result

        return wrapper

    @staticmethod
    def create_hash(namespace, func, *args, **kwargs):
        kwargs_list = []
        for key, value in kwargs.items():
            kwargs_list.append(f"{key}:{value}")
        return (
            namespace
            + ":"
            + func.__name__
            + " - "
            # + hashlib.sha256(func.__code__).hexdigest()
            + "|".join(str(arg if arg is not None else "None") for arg in args)
            + "|".join(kwargs_list)
        )
