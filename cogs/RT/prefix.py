# free RT - custom prefix

from typing import Literal

from discord.ext import commands

from util import db


class PrefixDB(db.DBManager):
    def __init__(self, bot):
        self.bot = bot

    async def manager_load(self, cursor):
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS UserPrefix (
            UserID BIGINT, Prefix TEXT)"""
        )
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS GuildPrefix (
            GuildID BIGINT, Prefix TEXT)"""
        )


class CustomPrefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.manager = await self.bot.add_db_manager(PrefixDB(self.bot))

    @commands.hybrid_command(
        aliases=["p", "プレフィックス", "プリフィックス", "接頭辞"],
        extras={
            "headding": {"ja": "プレフィックスを変更します。", "en": "Change prefix."},
            "parent": "RT"
        }
    )
    async def prefix(self, ctx, mode: Literal["server", "user"], new_prefix=None):
        # 未完成
        if new_prefix is None:
            await ctx.send({
                "ja": "カスタムプレフィックスを削除しました。",
                "en": "Deleted custom prefix."
            })
        await ctx.send({
            "ja": f"プレフィックスを{new_prefix}に変更しました。",
            "en": f"Changed prefix to {new_prefix}."
        })


async def setup(bot):
    await bot.add_cog(CustomPrefix(bot))
