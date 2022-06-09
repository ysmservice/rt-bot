# free RT - custom prefix

from typing import Literal

from discord.ext import commands
import discord

from util import db


class PrefixDB(db.DBManager):
    def __init__(self, bot):
        self.bot = bot

    @db.command()
    async def set_guild(self, cursor, id_: int, prefix: str) -> None:
        "サーバープレフィックスを設定します。"
        await cursor.execute(
            "SELECT * FROM GuildPrefix WHERE GuildID=%s", (id_,))
        if await cursor.fetchone():
            await cursor.execute(
                "UPDATE GuildPrefix SET Prefix=%s WHERE GuildID=%s",
                (prefix, id_,))
        else:
            await cursor.execute("INSERT INTO GuildPrefix VALUES (%s, %s)", (id_, prefix,))

        self.bot.guild_prefixes[id_] = prefix

    @db.command()
    async def set_user(self, cursor, id_: int, prefix: str) -> None:
        "ユーザープレフィックスを設定します。"
        await cursor.execute("SELECT * FROM UserPrefix WHERE UserID=%s", (id_,))
        if await cursor.fetchone():
            await cursor.execute("UPDATE GuildPrefix SET Prefix=%s WHERE GuildID=%s",
                                 (prefix, id_,))
        else:
            await cursor.execute("INSERT INTO GuildPrefix VALUES (%s, %s)", (id_, prefix,))

        self.bot.user_prefixes[id_] = prefix

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
    @app_commands.describe(mode="サーバーかユーザーか", new_prefix="設定する新しいプレフィックス")
    async def prefix(self, ctx, mode: Literal["server", "user"] = None, new_prefix: str = ""):
        """!lang ja
        --------
        カスタムプレフィックスの登録・変更・削除をします。
        登録をしても元々の`rf!`でも動作します。
        また、サーバー用・ユーザー用カスタムプレフィックスが両方指定されている場合はどちらでも動作します。

        Parameters
        ----------
        mode: `server`か`user`, optional
            `server`だとサーバー全体で、`user`だと個人で設定できます。
            指定しない場合は現在の設定を見ることができます。
        new_prefix: str, optional
            新しく設定するプレフィックスです。
            modeを指定してここを指定しなかった場合はカスタムプレフィックスを削除します。

        !lang en
        --------
        Set/Change/Delete custom prefix.
        `rf!` will be still working ever if it is set.

        Parameters
        ----------
        mode: `server` or `user`, optional
            If `server`, it sets to all the server members. If `user`, it sets to you only.
            If nothing here, you can view the custom prefix settings.
        new_prefix: str, optional
            Prefix that you want to set.
            If mode is set and here is nothing, custom prefix will be deleted.
        """
        modes_ja = {"server": "サーバー", "user": "ユーザー"}
        if not mode:
            # 現在の情報を表示する。
            await ctx.send(
                embed=discord.Embed(
                    title={"ja": "現在のprefix設定を見る", "en": "View prefix settings"},
                    description={
                        k: f"{j[0]} : `{self.bot.guild_prefixes.get(ctx.guild.id, '')}`\n" if ctx.guild else ""
                           + f"{j[1]} : `{self.bot.user_prefixes.get(ctx.author.id, '')}`"
                        for k, j in {
                            "ja": modes_ja.values(), "en": modes_ja.keys()
                        }.items()
                    }))

        if mode == "server" and not ctx.guild:
            raise commands.NoPrivateMessage()
        if mode == "server" and not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(["administrator"])

        await getattr(self.manager, f"set_{mode}").run(
            ctx.author.id if mode == "user" else ctx.guild.id,
            new_prefix
        )
        if new_prefix == "":
            await ctx.send({
                "ja": f"{modes_ja.get(mode)}のカスタムプレフィックスを削除しました。",
                "en": f"Deleted {mode.upper()} custom prefix."
            })
        await ctx.send({
            "ja": f"{modes_ja.get(mode)}のカスタムプレフィックスを{new_prefix}に変更しました。",
            "en": f"Changed {mode.upper()} custom prefix to {new_prefix}."
        })


async def setup(bot):
    await bot.add_cog(CustomPrefix(bot))
