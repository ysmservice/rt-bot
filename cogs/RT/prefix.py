# free RT - custom prefix

from typing import Literal

from discord.ext import commands

from util import db


class PrefixDB(db.DBManager):
    def __init__(self, bot):
        self.bot = bot

    @db.command()
    async def set_guild(self, cursor, id: int, prefix: str) -> None:
        "サーバープレフィックスを設定します。"
        pass

    async def manager_load(self, cursor) -> None:
        # テーブルの準備をし、データをメモリに保存しておく。
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS UserPrefix (
            UserID BIGINT, Prefix TEXT)"""
        )
        await cursor.execute("SELECT * FROM UserPrefix")
        self.bot.user_prefixes = dict(await cursor.fetchall())

        # サーバーprefix
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS GuildPrefix (
            GuildID BIGINT, Prefix TEXT)"""
        )
        await cursor.execute("SELECT * FROM GuildPrefix")
        self.bot.guild_prefixes = dict(await cursor.fetchall())


class CustomPrefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.manager = await self.bot.add_db_manager(PrefixDB(self.bot))

    @commands.hybrid_command(
        aliases=["p", "プレフィックス", "プリフィックス", "接頭辞"],
        extras={
            "headding": {"ja": "カスタムプレフィックスを設定します。", "en": "Set custom prefix."},
            "parent": "RT"
        }
    )
    async def prefix(self, ctx, mode: Literal["server", "user"], new_prefix=None):
        """!lang ja
        --------
        カスタムプレフィックスを登録・変更・削除します。
        登録をしても元々の`rf!`でも動作します。

        Parameters
        ----------
        mode: `server`か`user`
            `server`だとサーバー全体で、`user`だと個人で設定できます。
            どちらも設定されている場合はどちらでも動作します。
        new_prefix: str, optional
            新しく設定するプレフィックスです。
            指定しなかった場合はカスタムプレフィックスを削除します。

        !lang en
        --------
        Set/Change/Delete custom prefix.
        `rf!` will be still working ever if it is set.

        Parameters
        ----------
        mode: `server` or `user`
            If `server`, it sets to all the server members. If `user`, it sets to you only.
        new_prefix: str, optional
            Prefix that you want to set.
            If none has passed, custom prefix will be deleted.
        """
        # 未完成
        if new_prefix is None:
            await ctx.send({
                "ja": "カスタムプレフィックスを削除しました。",
                "en": "Deleted custom prefix."
            })
        await ctx.send({
            "ja": f"カスタムプレフィックスを{new_prefix}に変更しました。",
            "en": f"Changed custom prefix to {new_prefix}."
        })


async def setup(bot):
    await bot.add_cog(CustomPrefix(bot))
