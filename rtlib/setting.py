# RT Dashboard - Setting

from __future__ import annotations

from discord.ext import commands
import discord

from aiohttp import ClientSession

from rtlib.rt_module.src.setting import CommandData
from rtlib import RT


class Setting(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot
        self.data: dict[str, CommandData] = {}

    async def sync(self):
        self.data


def setup(bot):
    bot.add_cog(Setting(bot))