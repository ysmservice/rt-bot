# RT.AutoMod - Guild

from typing import TYPE_CHECKING, List

from ujson import loads, dumps
from functools import wraps
import discord

from .modutils import similer
from .types import Data

if TYPE_CHECKING:
    from aiomysql import Pool, Cursor
    from .__init__ import AutoMod


class DataManager:

    DB = "AutoMod"

    def __init__(self, cog: "AutoMod"):
        self.pool: "Pool" = cog.bot.mysql.pool
        self.cog = cog
        self.cog.bot.loop.create_task(self.prepare_table())

    async def prepare_table(self) -> None:
        """テーブルを作成します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.DB} (
                        GuildID BIGINT, Data JSON
                    );"""
                )

    async def _exists(self, cursor: "Cursor", guild_id: int) -> bool:
        # 渡されたCursorを使って存在確認を行う。
        await cursor.execute(
            f"SELECT GuildID FROM {self.DB} WHERE GuildID = %s;",
            (guild_id,)
        )
        return bool(await cursor.fetchone())

    async def get_guild(self, guild_id: int) -> "Guild":
        """サーバーのAutoModの設定用クラスを取得します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert await self._exists(cursor, guild_id), "見つかりませんでした。"
                await cursor.execute(
                    f"SELECT Data FROM {self.DB} WHERE GuildID = %s;",
                    (guild_id,)
                )
                return Guild(
                    self.cog, self.cog.bot.get_guild(guild_id),
                    loads((await cursor.fetchone())[0])
                )

    async def setup(self, guild_id: int) -> "Guild":
        """サーバーのAutoModの設定を登録します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert not await self._exists(cursor, guild_id), "既に登録されています。"
                await cursor.execute(
                    f"INSERT INTO {self.DB} VALUES (%s, %s);",
                    (guild_id, r"{}")
                )
                return Guild(self.cog, self.cog.bot.get_guild(guild_id), {})

    async def setdown(self, guild_id: int) -> None:
        """サーバーのAutoModの設定を削除します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert await self._exists(cursor, guild_id), "設定が見つかりませんでした。"
                await cursor.execute(
                    f"DELETE FROM {self.DB} WHERE GuildID = %s;",
                    (guild_id,)
                )


class Guild:

    AM = "[AutoMod]"
    MAX_INVITES = 100

    def __init__(
        self, cog: "AutoMod", guild: discord.Guild, data: Data
    ):
        self.pool: "Pool" = cog.bot.mysql.pool
        self.guild = guild
        self.cog = cog
        self.data: Data = data

        for key in ("warn",):
            if key not in self.data:
                self.data[key] = {}

    async def _commit(self) -> None:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"UPDATE {self.DB} SET Data = %s WHERE GuildID = %s;",
                    (dumps(self.data), self.guild.id)
                )

    @staticmethod
    def commit(func):
        @wraps(func)
        async def new(self, *args, **kwargs):
            data = await func(self, *args, **kwargs)
            await self._commit()
            return data
        return new

    @commit
    async def set_warn(self, user_id: int, warn: int) -> None:
        self.data["warn"][user_id] = warn

    @commit
    async def mute(self, warn: int, role_id: int) -> None:
        self.data["mute"] = (warn, role_id)

    @commit
    async def ban(self, warn: int) -> None:
        self.data["ban"] = warn

    @commit
    async def emoji(self, max_: int) -> None:
        self.data["emoji"] = max_

    @commit
    async def add_invite_channel(self, channel_id: int) -> None:
        if "invites" not in self.data:
            self.data["invites"] = []
        assert len(self.data["invites"]) + 1 == self.MAX_INVITES, "追加しすぎです。"
        self.data["invites"].append(channel_id)

    @commit
    async def remove_invite_channel(self, channel_id: int) -> None:
        if "invites" not in self.data:
            self.data["invites"] = []
        self.data["invites"].remove(channel_id)

    async def check_invite(self, invite: discord.Invite) -> None:
        if invite.channel.id in self.data.get("invites", ()):
            await invite.delete(
                reason=f"{self.AM}招待作成不可なチャンネルなため。"
            )

    @commit
    async def trigger_invite(self) -> bool:
        self.data["invite_filter"] = not self.data.get("invite_filter", False)
        return self.data["invite_filter"]

    @property
    def invites(self) -> List[int]:
        return self.data.get("invites", [])

    @commit
    async def level(self, level: int) -> None:
        self.data["level"] = level

    async def trial_message(self, content: str) -> None:
        ...