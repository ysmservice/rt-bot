import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(ban_members=True)
    @commands.command(aliases=["バン", "ばん", "BAN"])
    async def ban(self, ctx, *members):
        excepts = []
        for m in members:
            try:
                await ctx.guild.ban(m)
            except:
                excepts.append(m)
        if len(excepts) == 0:
            await ctx.reply("完了。", delete_after=5)
        else:
            await ctx.reply(f"BANを実行しました。\n(しかし、{', '.join(excepts)}のBANに失敗しました。)")

    @commands.has_permissions(kick_members=True)
    @commands.command(aliases=["キック", "きっく", "KICK"])
    async def kick(self, ctx, *members):
        excepts = []
        for m in members:
            try:
                await ctx.guild.kick(m)
            except:
                excepts.append(m)
        if len(excepts) == 0:
            await ctx.reply("完了。", delete_after=5)
        else:
            await ctx.reply(f"BANを実行しました。\n(しかし、{', '.join(excepts)}のBANに失敗しました。)")
