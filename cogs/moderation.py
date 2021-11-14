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
    async def ban(self, ctx, members, mode="ban"):
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
        members = [
            await commands.converter.MemberConverter().convert(ctx, member)
            for member in members
        ]
        excepts = []
        for m in members:
            try:
                await getattr(ctx.guild, mode)(m, reason=f"実行者:{ctx.author}")
            except:
                excepts.append(m)
        if excepts:
            mode = mode.upper()
            await ctx.reply(
                f"{mode}を実行しました。\n(しかし、{', '.join(map(str, excepts))}の{mode}に失敗しました。)",
                delete_after=5
            )
        else:
            await ctx.reply("ok", delete_after=5)

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
        await self.ban(ctx, *members, mode="kick")

    kick._callback.__doc__ = ban._callback.__doc__.replace("ban", "kick").replace("BAN", "Kick") \
        .replace("Ban", "Kick")


def setup(bot):
    bot.add_cog(Moderation(bot))
