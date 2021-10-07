# RT - TopGG

from discord.ext import commands, tasks
from topggpy import DBLClient


def setup(bot):
    if not hasattr(bot, "topgg") and not bot.test:
        bot.topgg = DBLClient(
            self.bot, bot.secret["topgg"],
            autopost=True, post_shard_count=True
        )