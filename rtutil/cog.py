# RT - Cog

import inspect


class Cog(type):
    def __new__(cls, name, bases, attrs):
        self = super().__new__(cls, name, bases, attrs)

        for key, value in attr.items():
            if inspect.iscoroutine(value):
                event_name = getattr(value, "__listener", None)
                if event_name:
                    self.bot.add_event(value, event_name)

        return self

    @classmethod
    def listener(cls, name=None):
        def decorator(function):
            if not inspect.iscoroutine(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.__listener = function.__name__
            return function
        return decorator

    @classmethod
    def commands
