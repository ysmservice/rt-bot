# rtlib.libs - On add/remove command

from discord.ext import commands
from copy import copy


class OnAddRemoveCommand(commands.Cog):
    """`on_command_add/remove`のイベントを追加することができるコグです。  
    イベント名の通りコマンドのついか/削除時に呼び出されます。  
    `bot.load_extension("rtlib.libs.on_command_add")`で使うことができます。""" # noqa
    def __init__(self, bot):
        self.bot = bot
        self._default_add_cmd = copy(self.bot.add_command)
        self._default_remvoe_cmd = copy(self.bot.remove_command)
        self.bot.add_command = self._on_add_command
        self.bot.remove_command = self._on_remove_command

    def _on_add_command(self, command: commands.Command):
        # discord.pyのコマンド追加関数にオーバーライドする関数です。
        self.bot.dispatch("command_add", command)
        return self._default_add_cmd(command)

    def _on_remove_command(self, command: commands.Command):
        # discord.pyのコマンド削除関数にオーバーラーイドする関数です。
        self.bot.dispatch("command_remove", command)
        return self._default_remove_cmd(command)


def setup(bot):
    bot.add_cog(OnAddRemoveCommand(bot))
