# RT - Servers

from typing import TYPE_CHECKING

from discord.ext import commands
import discord

from .server import Server
if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


class Servers(commands.Cog, Server):
    def __init__(self, bot):
        self.bot: "Backend" = bot
        self.pool: "Pool" = self.bot.mysql.pool
        self.bot.loop.create_task(self.init_table(self.pool))


def setup(bot):
    bot.add_cog(Servers(bot))