# rtutil - Setting Manager

from discord.ext import commands
import discord

from typing import TypedDict, Union


class SettingData(TypedDict):
    callback: Callable
    permission: discord.Permissions
    type: Literal["guild", "user"]


class SettingManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if "OnCommandAdd" not in self.bot.cogs:
            raise Exception("SettingManagerはrtlib.libs.on_command_addが必要です。")
        self.data = {}

    @commands.Cog.listener()
    async def on_command_add(self, command):
        data: Union[SettingData, None] = command.extras.get("on_setting")
        if data:
            self.data[command.qualified_name] = data

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        if "on_setting" in command.extras:
            self.data.pop(command.qualified_name, None)


def setup(bot):
    bot.add_cog(SettingManager(bot))
