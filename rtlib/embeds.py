"""準備中..."""

from discord.ext import commands


class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if "Componesy" not in self.bot.cogs:
            self.bot.load_extension("rtlib.componesy")

    async def 