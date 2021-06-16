# RT - Cog

import asyncio


class Cog(type):
    def __new__(cls, name, bases, attrs):
        self = super().__new__(cls, name, bases, attrs)

        i = self.__init__
        def _init(_self, *args, **kwargs):
            # 追加するイベントなどの追加して欲しいもののリストを作る。
            # 型はリストではなく辞書です。リストの方がわかりやすいからリストとかいた。
            _self.coros = {}
            for key in attrs:
                coro = getattr(_self, key, None)
                if coro:
                    for check in ("event", "command", "route"):
                        k = getattr(coro, check, None)
                        if k:
                            _self.coros[key] = {
                                "args": k[0],
                                "kwargs": k[1],
                                "mode": check,
                                "coro": coro
                            }
                            break
            i(_self, *args, **kwargs)
        self.__init__ = _init

        return self

    @classmethod
    def get_filename(cls):
        return __name__

    @classmethod
    def listener(cls, *args, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.event = (args, kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator

    @classmethod
    def command(cls, *args, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.command = (args, kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator

    @classmethod
    def route(cls, *args, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.route = (args, kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator
