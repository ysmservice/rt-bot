# free RT - Feature for Developers

from discord.ext import commands

from util import RT


class Develop(commands.Cog):
    
    def __init__(self, bot: RT):
        self.bot = bot
    
    @commands.group()
    @commands.is_owner()
    async def develop(self, ctx):
        if not ctx.invoked_subcommand is None:
            return await ctx.send("使用方法が違います。")
    
    @develop.command()
    async def reload_help(self, ctx, command_name = None):
        if command_name is None:
            for c in self.bot.commands:
                await self.bot.cogs["DocHelp"].on_command_add(c)
            await ctx.send("全コマンドのhelp読み込み完了")
        else:
            for c in [self.bot.get_command(co) for co in command_name.split()]:
                await self.bot.cogs["DocHelp"].on_command_add(c)
            await ctx.send(f"{', '.join(command_name.split())}のhelp読み込み完了")


def setup(bot):
    bot.add_cog(Develop(bot))
