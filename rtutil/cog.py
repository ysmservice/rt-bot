# RT - Cog

import inspect


class Cog(type):
    def __new__(cls, name, bases, attrs):
        self = super().__new__(cls, name, bases, attrs)

        for key, value in attr.items():
            if inspect.iscoroutine(value):
                event_name = getattr(value, "__listener", None)
                command = getattr(value, "__command", None)
                if event_name:
                    self.bot.add_event(value, event_name)
                elif command:
                    args, kwargs = command
                    self.bot.add_command(value, *args, **kwargs)

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
    def commands(cls, *args, **kwargs):
        def decorator(function):
            if not inspect.iscoroutine(function):
                raise TypeError("The function is not coroutine.")
            function.__command = (args, kwargs)
            return function
        return decorator
