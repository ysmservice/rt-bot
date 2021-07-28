# rtlib.libs - Useful Help

from discord.ext import commands


class UsefulHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        # on_command_addが必要なのでロードされてないならロードする。
        if "OnAddRemoveCommand" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_command_add")

    @commands.Cog.listener()
    async def on_command_add(self, command: commands.Command):
        self.data
