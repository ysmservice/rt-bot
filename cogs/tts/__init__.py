# RT - TTS

from discord.ext import commands

from rtlib import RT


class TTSCog(commands.Cog, name="TTS"):
    def __init__(self, bot: RT):
        self.bot = bot


def setup(bot):
    bot.add_cog(TTSCog(bot))