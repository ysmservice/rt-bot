# RT - Cog

import asyncio
from .worker import NOT_COROUTINE_EVENTS


def make_decorator(cls, mode, args, kwargs):
    def decorator(function):
        if asyncio.iscoroutinefunction(function):
            if mode == "event":
                en = args[0] if args else function.__name__
                if en in NOT_COROUTINE_EVENTS:
                    raise TypeError(
                        "rtutil.NOT_COROUTINE_EVENTSにあるイベントはコルーチンである必要があります。")
        else:
            if mode == "event":
                en = args[0] if args else function.__name__
                if en not in NOT_COROUTINE_EVENTS:
                    raise TypeError("登録する関数はコルーチンにする必要があります。")
            else:
                raise TypeError("登録する関数はコルーチンにする必要があります。")
        exec(
            "function." + mode + " = (args, kwargs)",
            {"args": args, "kwargs": kwargs, "function": function}
        )
        function.__cog_name = cls.__name__
        return function
    return decorator


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
        return make_decorator(cls, "event", args, kwargs)

    @classmethod
    def event(cls, *args, **kwargs):
        return make_decorator(cls, "event", args, kwargs)

    @classmethod
    def command(cls, *args, **kwargs):
        return make_decorator(cls, "command", args, kwargs)

    @classmethod
    def route(cls, *args, **kwargs):
        return make_decorator(cls, "route", args, kwargs)
