# RT Util - Data Manager

from typing import Callable, Coroutine

from inspect import iscoroutinefunction
from functools import wraps


class DatabaseManager:
    def __init_subclass__(cls):
        for key in dir(cls):
            coro = getattr(cls, key)
            if iscoroutinefunction(coro):
                if "cursor" in coro.__annotations__:
                    setattr(cls, coro.__name__, cls.wrap(coro))

    @staticmethod
    def wrap(coro: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        "自動的にCursorがキーワード引数に渡されるようにするデコレータです。"
        @wraps(coro)
        async def new_coro(self, *args, **kwargs):
            conn = None
            if "cursor" not in kwargs:
                conn = await self.pool.acquire()
                kwargs["cursor"] = await conn.cursor()
            try:
                data = await coro(self, *args, **kwargs)
            except Exception as e:
                await kwargs["cursor"].close()
                if conn:
                    conn.close()
                raise e
            finally:
                await kwargs["cursor"].close()
                if conn:
                    conn.close()
            return data
        return new_coro