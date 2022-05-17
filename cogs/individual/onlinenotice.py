# Free RT - online Notice

from discord.ext import commands
import discord

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
            "SELECT * FROM OnlineNotice WHERE notice_user=?",
            (author_id,)
        )
        return await cursor.fetchall()

    @db.command()
    async def set_user(self, cursor, author_id: int, notice_user_id: int) -> None:
        "データを入れます。author_id: 通知する人 notice_user_id: 監視される人"
        if now := self.get_user(cursor, author_id):
            data = dumps(loads(now[1]) + [str(author_id)])
            await cursor.execute(
                "UPDATE OnlineNotice SET authors=? WHERE notice_user=?",
                (data, notice_user_id)
            )
        else:
            await cursor.execute(
                "INSERT INTO OnlineNotice values (?, ?)",
                (notice_user_id, (dumps([str(author_id)])))
            )


class OnlineNotice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.db = await self.bot.add_db_manager(DataBaseManager(self.bot))

    @commands.group(
        extras={
            "headding": {"ja": "オンライン通知", "en": "Online Notice"},
            "parent": "Individual"
        }
    )
    async def online_notice(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("使用方法が違います。")

    @online_notice.command(name="set")
    async def _set(self, ctx, notice_user: discord.User):
        await self.db.set_user.run(ctx.auhtor.id, notice_user.id)
        await ctx.send("Ok")

    # require: presence_intent

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.status == after.status:
            return
        if after.status != discord.Status.online:
            return

        userdata = await self.db.get_user.run(after.id)
        if userdata:
            for m in loads(userdata[1]):
                try:
                    e = discord.Embed(title="オンライン通知", descrption=f"{after.mention}さんがオンラインになりました。")
                    await bot.get_user(int(m)).send(embed=e)
                except Exception:
                    pass


async def setup(bot):
    await bot.add_cog(OnlineNotice(bot))