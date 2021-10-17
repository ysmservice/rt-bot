import discord
from discord.ext import commands
from typing import List

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(ban_members=True)
    @commands.command(
        extras={
            "headding": {
                "ja": "メンバーのBAN",
                "en": "BAN members"
            }, "parent": "ServerSafety"
        }, aliases=["バン", "ばん", "BAN"]
    )
    async def ban(self, ctx, *members: List[discord.Member]):
        """!lang ja
        --------
        メンバーをBANできます。

        Parameters
        ----------
        members : メンバーのメンションか名前
            誰をBANするかです。  
            空白で区切って複数人指定もできます。

        !lang en
        --------
        Ban members

        Parameters
        ----------
        members : Mention or Name of members
            Target members.

        Examples
        --------
        `rt!ban @tasuren @tasuren-sub`"""
        excepts = []
        for m in members:
            try:
                await ctx.guild.ban(m, reason=f"実行者:{ctx.author}")
            except:
                excepts.append(m)
        if len(excepts) == 0:
            await ctx.reply("完了。", delete_after=5)
        else:
            await ctx.reply(
                f"BANを実行しました。\n(しかし、{', '.join(excepts)}のBANに失敗しました。)",
                delete_after=5
            )

    @commands.has_permissions(kick_members=True)
    @commands.command(
        extras={
            "headding": {
                "ja": "メンバーのキック",
                "en": "Kick members"
            }, "parent": "ServerSafety"
        }, aliases=["キック", "きっく", "KICK"]
    )
    async def kick(self, ctx, *members: List[discord.Member]):
        """!lang ja
        --------
        メンバーをキックできます。

        Parameters
        ----------
        members : メンバーのメンションか名前
            誰をキックするかのメンションです。  
            空白で区切って複数人指定もできます。

        !lang en
        --------
        Kick members

        Parameters
        ----------
        members : Mention or Name of members
            Target members

        Examples
        --------
        `rt!kick @tasuren @tasuren-sub`"""
        excepts = []
        for m in members:
            try:
                await ctx.guild.kick(m, reason=f"実行者:{ctx.author}")
            except:
                excepts.append(m)
        if len(excepts) == 0:
            await ctx.reply("完了。", delete_after=5)
        else:
            await ctx.reply(
                f"キックを実行しました。\n(しかし、{', '.join(excepts)}のキックに失敗しました。)",
                delete_after=5
            )

def setup(bot):
    bot.add_cog(Moderation(bot))
