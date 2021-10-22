# RT - Role Keeper

from typing import TYPE_CHECKING, Optinal, List

from discord.ext import commands
import discord

if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


TABLES = ("RoleKeeper", "RoleKeeperData", "RoleKeeperExceptions")


class DataManager:
    def __init__(self, cog: "RoleKeeper"):
        self.cog = self.cog
        self.pool: "Pool" = self.cog.mysql.pool
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self) -> None:
        # データベースにテーブルを作ります。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {TABLES[0]} VALUES (GuildID BIGINT);"
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
                        f"UPDATE {TABLES[1]} SET Roles = %s;", (roles,)
                    )
                else:
                    await cursor.execute(
                        f"INSERT INTO {TABLES[1]} (%s, %s, %s);",
                        (guild_id, user_id, roles)
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


class RoleKeeper(commands.Cog, DataManager):
    def __init__(self, bot: "Backend"):
        self.bot = bot
        super(commands.Cog, self).__init__(self)

    @commands.group(aliases=["rk", "ロールキーパー"])
    async def rolekeeper(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.trigger_typing()
            onoff = await self.toggle(ctx.guild.id)
            await ctx.reply(
                {"ja": f"ロールキーパーを{'ON' if onoff else 'OFF'}にしました。にしました。"
                 "en": f"RoleKeeper is {'en' if onoff else 'dis'}abled."}
            )

    @commands.Cog.listener()