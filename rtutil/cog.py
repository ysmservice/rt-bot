# RT - Cog

import asyncio


def _inject(attrs, worker):
    # ひとつづつ追加されるコグにある関数を取り出す。
    # そしてコマンドかイベントリスナーを登録する。
    # コマンドかイベントリスナーか確認する方法は以下の通り。
    # コマンドかイベントリスナーにつけたデコレ―タが呼び出されたら、イベントまたはコマンドの名前を設定しておく。
    # Example : function.listener = <event_name>
    # そしてここでとりだした関数から上のをとって確認する。
    # 確認したら登録してあげる。
    for key, value in attrs.items():
        # コルーチンだけチェックする。
        if asyncio.iscoroutinefunction(value):
            # ここでコマンドかイベントリスナーの名前をあったら取得する。
            event_name = getattr(value, "listener", None)
            command = getattr(value, "command", None)
            route = getattr(value, "route", None)
            # 取得できたなら登録してあげる。
            if event_name:
                event_name, kwargs = event_name
                worker.add_event(value, event_name, **kwargs)
            elif command:
                command_name, kwargs = command
                worker.add_command(
                    value, command_name=command_name, **kwargs)
                worker.commands.append(value)
            elif route:
                uri, args, kwargs = route
                worker.add_route(value, uri)


class Cog(type):
    def __new__(cls, name, bases, attrs):
        self = super().__new__(cls, name, bases, attrs)
        self.attrs = attrs
        return self

    @classmethod
    def get_filename(cls):
        return __name__

    @classmethod
    def listener(cls, name=None, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.listener = (name if name else function.__name__,
                                   kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator

    @classmethod
    def command(cls, command_name: str = None, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.command = (command_name
                                  if command_name else function.__name__,
                                  kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator

    @classmethod
    def route(cls, uri: str = "/", *args, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.route = (uri, args, kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator
