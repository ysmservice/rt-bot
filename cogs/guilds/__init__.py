# RT - Guilds

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from rtlib import Backend


class Guilds(commands.Cog):
    def __init__(self, bot: "Backend"):
        self.bot = bot