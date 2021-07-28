# rtlib.libs - On add/remove command

from discord.ext import commands
from copy import copy


class OnAddRemoveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._default_add_cmd = copy(self.bot.add_command)
        self._default_remvoe_cmd = copy(self.bot.remove_command)
        self.bot.add_command = self._add_command
        self.bot.remove_command = self._remove_command

    def _add_command(self)
