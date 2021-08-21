"""`on_command_add/remove`のイベントを追加することができるエクステンションです。  
イベント名の通りコマンドのついか/削除時に呼び出されます。  
`bot.load_extension("rtlib.ext.on_command_add")`で有効化することができます。  
また`rtlib.setup(bot)`でも有効化することができます。  
これを使用して追加されるイベントには`discord.ext.commands.Command`が渡されます。"""

from typing import Literal, Callable
from functools import wraps

from discord.ext import commands
from copy import copy


class OnCommandAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # discord.pyのadd/remove_commandをオーバーライドする。
        for mode, default, parent in (
                ("add", commands.Bot.add_command, "commands.Bot"),
                ("remove", commands.Bot.remove_command, "commands.Bot"),
                ("add", commands.Group.add_command, "commands.Group"),
                ("remove", commands.Group.remove_command, "commands.Group")):
            setattr(
                eval(parent), default.__name__,
                self._make_on_addremove_command(mode, copy(default), parent)
            )

    def _make_on_addremove_command(self, mode: str, original: Callable, parent) -> Callable:
        # オーバーライドするためのon_add/remove_commmandの関数を作るための関数です。

        @wraps(original)
        def new_function(original_self, command):
            # オーバーライドされたオリジナルを実行する。
            command = original(original_self, command) or command
            self.bot.dispatch(f"command_{mode}", command)
            print(mode, parent, command.qualified_name)
            return command

        return new_function


def setup(bot):
    bot.add_cog(OnCommandAdd(bot))
