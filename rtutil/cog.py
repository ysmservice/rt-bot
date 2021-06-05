# RT - Cog

import asyncio


class Cog(type):
    def __new__(cls, name, bases, attrs):
        self = super().__new__(cls, name, bases, attrs)

        # ひとつづつ追加されるコグにある関数を取り出す。
        # そしてコマンドかイベントリスナーを登録する。
        # コマンドかイベントリスナーか確認する方法は以下の通り。
        # コマンドかイベントリスナーにつけたデコレ―タが呼び出されたら、イベントまたはコマンドの名前を設定しておく。
        # Example : function.__listener = <event_name>
        # そしてここでとりだした関数から上のをとって確認する。
        # 確認したら登録してあげる。
        for key, value in attrs.items():
            # コルーチンだけチェックする。
            if asyncio.iscoroutinefunction(value):
                # ここでコマンドかイベントリスナーの名前をあったら取得する。
                event_name = getattr(value, "__listener", None)
                command = getattr(value, "__command", None)
                # 取得できたなら登録してあげる。
                if event_name:
                    event_name, kwargs = event_name
                    self.bot.add_event(value, event_name, **kwargs)
                elif command:
                    command_name, kwargs = command
                    self.bot.add_command(
                        value, command_name=command_name, **kwargs)
                    self.commands.append(value)

        return self

    @classmethod
    def get_filename(cls):
        return __name__

    @classmethod
    def listener(cls, name=None, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.__listener = (name if name else function.__name__,
                                   kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator

    @classmethod
    def command(cls, command_name=None, **kwargs):
        def decorator(function):
            if not asyncio.iscoroutinefunction(function):
                raise TypeError("登録する関数はコルーチンにする必要があります。")
            function.__command = (command_name
                                  if command_name else function.__name__,
                                  kwargs)
            function.__cog_name = cls.__name__
            return function
        return decorator
