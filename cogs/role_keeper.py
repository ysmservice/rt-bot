# RT - Role Keeper

from typing import TYPE_CHECKING, Optional, List

from discord.ext import commands, tasks
import discord

from time import time

if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


# データベースのテーブルです。
TABLES = ("RoleKeeper", "RoleKeeperData", "RoleKeeperExceptions")
# デフォルトのどれだけ放置されたらそのロールデータを削除するかの秒数です。(三ヶ月)
DEFAULT_GHOST_TIME = 7884000


class DataManager:
    def __init__(self, cog: "RoleKeeper"):
        self.cog = cog
        self.pool: "Pool" = self.cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self) -> None:
        # データベースにテーブルを作ります。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {TABLES[0]} VALUES (GuildID BIGINT);"
                )
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {TABLES[1]} VALUES (
                        GuildID BIGINT, UserID BIGINT, Roles TEXT, UpdateTime FLOAT
                    );"""
                )

    async def toggle(self, guild_id: int) -> bool:
        """ロールキーパーを有効または無効にします。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {TABLES[0]} WHERE GuildID = %s;",
                    (guild_id,)
                )
                if await cursor.fetchone():
                    # 設定を削除する。
                    await cursor.execute(
                        f"DELETE FROM {TABLES[0]} WHERE GuildID = %s;",
                        (guild_id,)
                    )
                    # 保存されているロールデータを削除する。
                    await cursor.execute(
                        f"SELECT GuildID FROM {TABLES[1]} WHERE GuildID = %s;",
                        (guild_id,)
                    )
                    if await cursor.fetchone():
                        await cursor.execute(
                            f"DELETE FROM {TABLES[1]} WHERE GuildID = %s;",
                            (guild_id,)
                        )
                    return False
                else:
                    # 設定を追加する。
                    await cursor.execute(
                        f"INSERT INTO {TABLES[0]} (%s);",
                        (guild_id)
                    )
                    return True

    async def check(self, guild_id: int) -> bool:
        """指定されたサーバーがロールキーパーを有効にしているかを確認します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT GuildID FROM {TABLES[0]} WHERE GuildID = %s;",
                    (guild_id,)
                )
                return bool(await cursor.fetchone())

    async def write_roledata(
        self, guild_id: int, user_id: int, roles: List[int]
    ) -> None:
        """ロールデータを書き込みます。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                roles = ",".join(map(str, roles))
                await cursor.execute(
                    f"SELECT GuildID FROM {TABLES[1]} WHERE GuildID = %s AND UserID = %s;",
                    (guild_id, user_id)
                )
                if await cursor.fetchone():
                    await cursor.execute(
                        f"UPDATE {TABLES[1]} SET Roles = %s, UpdateTime = %s;",
                        (roles, time())
                    )
                else:
                    await cursor.execute(
                        f"INSERT INTO {TABLES[1]} (%s, %s, %s, %s);",
                        (guild_id, user_id, roles, time())
                    )

    async def read_roledata(
        self, guild_id: int, user_id: int
    ) -> List[int]:
        """ロールデータを取得します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT Roles FROM {TABLES[1]} WHERE GuildID = %s AND UserID = %s;",
                    (guild_id, user_id)
                )
                assert (row := await cursor.fetchone()), "ロールデータは書き込まれていません。"
                return list(map(int, row[0].split(",")))

    @tasks.loop(minutes=3)
    async def delete_ghost(self) -> None:
        """三ヶ月以上放置されていないユーザーのロールデータは削除する。"""
        now = time()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM {TABLES[1]};")

                for row in await cursor.fetchall():
                    if now - row[2] > DEFAULT_GHOST_TIME:
                        # もしDEFAULT_GHOST_TIME秒放置されているロールデータがあるなら削除する。
                        await cursor.execute(
                            f"DELETE FROM {TABLES[1]} WHERE GuildID = %s AND UserID = %s;",
                            (row[0], row[1])
                        )


class RoleKeeper(commands.Cog, DataManager):
    def __init__(self, bot: "Backend"):
        self.bot = bot
        self.delete_ghost.start()
        super(commands.Cog, self).__init__(self)

    @commands.group(aliases=["rk", "ロールキーパー"])
    async def rolekeeper(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.trigger_typing()
            onoff = await self.toggle(ctx.guild.id)
            await ctx.reply(
                {"ja": f"ロールキーパーを{'ON' if onoff else 'OFF'}にしました。にしました。",
                 "en": f"RoleKeeper is {'en' if onoff else 'dis'}abled."}
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # メンバーが参加した際にもしロールデータがあるならそのロールを付与しておく。
        if (roles := await self.read_roledata(member.guild.id, member.id)):
            for role in roles:
                if (role := member.guild.get_role(role.id)):
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if await self.check(member.guild.id):
            # 退出したメンバーがいたらその人のロールデータを保存しておく。
            await self.write_roledata(
                member.guild.id, member.id, [r.id for r in member.roles]
            )

    def cog_unload(self):
        self.delete_ghost.cancel()


def setup(bot):
    bot.add_cog(RoleKeeper(bot))
