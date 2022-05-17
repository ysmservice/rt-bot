# Free RT - online Notice

from discord.ext import commands
import discord

import asyncio

from ujson import loads, dumps

from util import db


class DataBaseManager(db.DBManager):
    def __init__(self, bot):
        self.bot = bot

    async def manager_load(self, cursor):
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS
            OnlineNotice (notice_user BIGINT, authors TEXT)"""
        )

    @db.command()
    async def get_user(self, cursor, notice_user_id: int) -> tuple:
        "データを取得します。"
        await cursor.execute(
            f"SELECT * FROM OnlineNotice WHERE notice_user={notice_user_id}"
        )
        return await cursor.fetchall()

    @db.command()
    async def set_user(self, cursor, author_id: int, notice_user_id: int) -> None:
        "データを入れます。author_id: 通知する人 notice_user_id: 監視される人"
        if now := await self.get_user(cursor, author_id):
            data = dumps(loads(now[1]) + [str(author_id)])
            await cursor.execute(
                f"UPDATE OnlineNotice SET authors='{data}' WHERE notice_user={notice_user_id}",
                (data, notice_user_id)
            )
        else:
            await cursor.execute(
                f"INSERT INTO OnlineNotice values ({notice_user_id}, '{dumps([str(author_id)])}')"
            )


class OnlineNotice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = []

    async def cog_load(self):
        self.db = await self.bot.add_db_manager(DataBaseManager(self.bot))

    @commands.group(
        extras={
            "headding": {"ja": "オンライン通知", "en": "Online Notice"},
            "parent": "Individual"
        }
    )
    async def online_notice(self, ctx):
        """!lang ja
        --------
        ユーザーがオンラインになったときに通知します。

        !lang en
        --------
        Notices if a user was online."""
        if ctx.invoked_subcommand is None:
            await ctx.send("使用方法が違います。")

    @online_notice.command(
        name="add", aliases=["set", "追加", "設定"],
        extras={"ja": "通知するユーザーを追加", "en": "Add notice user"}
    )
    async def _add(self, ctx, notice_user: discord.User):
        """!lang ja
        --------
        通知するユーザーを追加します。

        Parameters
        ----------
        notice_user: ユーザーIDか名前かメンション
            このユーザーがオンラインになった時にあなたのDMに通知が来ます。

        Aliases
        -------
        set, 追加, 設定

        !lang en
        --------
        Adds the user to notice list.

        Parameters
        ----------
        notice_user: User ID, name, or mention
            Notice message will come to your DM when the user becomes online.

        Aliases
        -------
        set
        """
        await self.db.set_user.run(ctx.author.id, notice_user.id)
        await ctx.send("Ok")

    # require: presence_intent

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.status == after.status:
            return
        if after.status != discord.Status.online:
            return
        if after.id in self.cache:
            return

        userdata = await self.db.get_user.run(after.id)
        if userdata:
            self.cache.append(after.id)
            for m in loads(userdata[0][1]):
                try:
                    e = discord.Embed(title="オンライン通知", description=f"{after.mention}さんがオンラインになりました。")
                    await self.bot.get_user(int(m)).send(embed=e)
                except Exception:
                    pass
            await asyncio.sleep(0.5)
            self.cache.remove(after.id)


async def setup(bot):
    await bot.add_cog(OnlineNotice(bot))
