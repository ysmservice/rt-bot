# RT - Url Checker

from typing import TYPE_CHECKING

from discord.ext import commands
import discord

from bs4 import BeautifulSoup
from rtutil import securl

if TYPE_CHECKING:
    from rtlib import Backend


class UrlChecker(commands.Cog):
    def __init__(self, bot: "Backend"):
        self.bot = bot

    @commands.command()
    async def check(self, ctx: commands.Context, *, url: str):
        await ctx.trigger_typing()
        data = await securl.check(self.bot.session, url)
        embed = discord.Embed(
            title=self.__cog_name__,
            color=self.bot.colors["normal"]
        )
        embed.set_image(
            url=securl.get_capture(data)
        )
        await ctx.reply(
            embed=embed
        )


def setup(bot):
    bot.add_cog(UrlChecker(bot))