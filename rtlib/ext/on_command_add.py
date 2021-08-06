"""`on_command_add/remove`のイベントを追加することができるエクステンションです。  
イベント名の通りコマンドのついか/削除時に呼び出されます。  
`bot.load_extension("rtlib.ext.on_command_add")`で使うことができます。
これを使用して追加されるイベントには`discord.ext.commands.Command`が渡されます。"""

from typing import Literal, Callable

from discord.ext import commands
from copy import copy


class OnCommandAdd(commands.Cog):

    ON_ADD_COMMAND = """def !parent!(command):
    # もしグループコマンドならそのグループのadd/remove_commandをオーバーライドする。
    if isinstance(command, commands.Group):
        command = self._on_group_addremove(command)
    # グループコマンドに登録されているコマンドはself.queueに追加される。
    # そのself.queueにあるコマンドでon_command_addの呼び出しをする。それと本命の方。
    queue_done = None
    for cmd in [command] + self.queue.get(command.name, []):
        if cmd.name != command.name:
            queue_done = command.name
        self.bot.dispatch("command_add", cmd)
    # もしqueueを処理したのならそのqueueを削除する。
    if queue_done is not None:
        del self.queue[queue_done]
    # オーバーライドされたオリジナルを実行する。
    return self._default_add_cmd_!parent_onlyname!(command)
self.!parent! = !parent!"""
    ON_REMOVE_COMMAND = """def !parent!(name):
    command = self._default_remove_cmd_!parent_onlyname!(name)
    self.bot.dispatch("command_remove", command)
    return name
self.!parent! = !parent!"""

    def __init__(self, bot):
        self.bot = bot
        # discord.pyのadd/remove_commandをオーバーライドする。
        for mode, default in (("add", self.bot.add_command),
                              ("remove", self.bot.remove_command)):
            setattr(
                self.bot, mode + "_command",
                self._make_on_addremove_command(
                    mode, "normal", copy(default)
                )
            )
        self.queue = {}

    def _make_on_addremove_command(self, mode: Literal["add", "remove"],
                                   parent: str, original: Callable) -> Callable:
        # オーバーライドするためのon_add/remove_commmandの関数を作るための関数です。
        code = self.ON_ADD_COMMAND if mode == "add" else self.ON_REMOVE_COMMAND
        setattr(self, f"_default_{mode}_cmd_{parent}", original)
        function_name = f"_on_{mode}_command_{parent}"
        exec(code
                 .replace("!parent!", function_name)
                 .replace("!parent_onlyname!", parent),
             {"self": self, "commands": commands}
        )
        return eval("self." + function_name)

    def _on_group_addremove(self, command):
        # グループコマンドが追加された際に呼び出される関数です。
        # グループコマンドに登録されているコマンドをグループコマンド
        self.queue[command.name] = [cmd for cmd in command.commands]
        # グループのadd/remove_commandをオーバーライドする。
        command.add_command = self._make_on_addremove_command(
            "add", command.name, copy(command.add_command)
        )
        command.remove_command = self._make_on_addremove_command(
            "remove", command.name, copy(command.remove_command)
        )
        return command


def setup(bot):
    bot.add_cog(OnCommandAdd(bot))
