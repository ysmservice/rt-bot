# RT.servers - Server Class
# サーバーの情報をしまってraiseなどを簡単に行うためのクラスです。
# セーブデータの操作もこのクラスで行います。

from typing import TYPING_CHECK, List, Union

import discord

from ujson import dumps, loads
from time import time

from .constants import DB, INTERVAL, MAX_DETAIL, MAX_TAGS, MAX_TAG
if TYPING_CHECK:
    from aiomysql import Pool, Cursor
    from .__init__ import Servers


class Server:
    def __init__(
        self, cog: "Servers", guild: discord.Guild,
        description: str, tags: List[str], invite: str,
        before_raise: int, extra: dict
    ):
        self.cog: "Servers" = cog
        self.guild: discord.Guild = guild
        self.description: str = description
        self.tags: List[str] = tags
        self.before_raise: int = before_raise
        self.invite: str = invite
        self.extra: dict = extra

    @staticmethod
    def check(*, tags: List[str] = [], description: str = "") -> None:
        assert len(tags) <= MAX_TAGS, f"タグは{MAX_TAGS}個までである必要があります。。"
        assert all(
            len(tag) <= MAX_TAG for tag in tags
        ), f"タグの名前は{MAX_TAG}文字までである必要があります。"
        assert len(description) <= MAX_DETAIL, f"説明欄は{MAX_DETAIL}文字までしか入れられません。"

    async def raise_server(self, force: bool = False) -> None:
        # サーバーの表示順位を上げます。
        now = time()
        assert force or now - self.before_raise >= INTERVAL, "まだ高められません。"
        self.before_raise = now

        async with self.cog.pool.acquire() as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                f"""--sql
                UPDATE {DB}
                SET RaiseTime = %s
                WHERE GuildID = %s;""",
                (now, self.guild.id)
            )
            await cursor.close()

    async def update_data(
        self, *, description: str = None, tags: List[str] = None, invite: str = None
    ) -> None:
        # サーバーの情報を更新します。
        self.check_tags(tags=tags, description=description)

        self.tags = tags or self.tags
        args = (
            description or self.description,
            ",".join(self.tags), invite or self.invite,
            self.guild.id
        )
        self.description = args[0]
        self.invite = args[2]

        async with self.cog.pool.acquire() as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                f"""--sql
                UPDATE {DB}
                SET
                    Detail = %s,
                    Tags = %s,
                    Invite = %s
                WHERE
                    GuildID = %s;""", args
            )
            await cursor.close()

    async def update_extra(self, extra: dict) -> None:
        # サーバーのエキストラの情報を更新します。
        self.extra.update(extra)
        async with self.cog.pool.acquire() as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                f"""--sql
                UPDATE {DB}
                SET
                    Extra = %s
                WHERE
                    GuildID = %s;""",
                (dumps(self.extra, ensure_ascii=False),
                 self.guild.id)
            )
            await cursor.close()

    @staticmethod
    async def exists(
        cog: "Servers", guild_id: int, cursor: "Cursor",
        error_message: str, not_: bool = True
    ) -> None:
        await cursor.execute(
            f"""--sql
            SELECT * FROM {DB}
            WHERE GuildID = %s
            LIMIT 1;""", (guild_id,)
        )

        b = bool(await cursor.fetchone())
        if not_:
            b = not b
        assert b, error_message

    @classmethod
    async def from_guild(
        cls, cog: "Servers", guild: discord.Guild,
        cursor: "Cursor" = None
    ) -> "Server":
        # GuildオブジェクトからServerクラスを取得します。
        close = True
        if cursor is None:
            conn = await cog.pool.acquire()
            cursor = await conn.cursor()
            close = False

        await cursor.execute(
            f"""--sql
            SELECT * FROM {DB}
            WHERE GuildID = %s;""",
            (guild.id,)
        )
        row = await cursor.fetchone()

        if close:
            await cursor.close()
            await conn.close()

        assert row, "そのサーバーは登録されていません。"

        return cls(
            cog, guild, row[1], row[2].split(","),
            row[3], row[4], loads(row[5])
        )

    @classmethod
    async def make_guild(
        cls, cog: "Servers", guild: discord.Guild,
        description: str, tags: List[str],
        invite: str, extra: dict
    ) -> "Server":
        # サーバーを追加します。
        cls.check_tags(tags=tags, description=description)

        async with cog.pool.acquire() as conn:
            cursor = await conn.cursor()

            await cog.exists(cog, guild.id, cursor, "既に登録されています。")

            await cursor.execute(
                f"""--sql
                INSERT INTO {DB} (
                    GuildID, Detail, Tags,
                    RaiseTime, Extra
                )
                VALUES (%s, %s, %s, %s, %s, %s);""",
                (
                    guild.id, description, ",".join(tags),
                    invite, now := time(), dumps(extra)
                )
            )
            await cursor.close()

        return cls(
            cog, guild, description, tags,
            invite, now, extra
        )

    @staticmethod
    async def init_table(pool: "Pool") -> None:
        # データベースのテーブルの準備をします。
        async with pool.acquire() as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                f"""--sql
                CREATE TABLE {DB}
                (
                    GuildID BIGINT NOT NULL PRIMARY KEY,
                    Detail TEXT, Tags TEXT, RaiseTime FLOAT,
                    Invite TEXT, Extra JSON
                );"""
            )
            await cursor.close()

    @staticmethod
    async def delete_guild(cog: "Servers", guild_id: int) -> None:
        # データベースからサーバーを登録解除します。
        async with cog.pool.acquire() as conn:
            cursor = await conn.cursor()

            await cog.exists(cog, guild_id, cursor, "まだ登録されていません。", False)
            await cursor.execute(
                f"""--sql
                DELETE FROM {DB}
                WHERE GuildID = %s;""",
                (guild_id,)
            )

            await cursor.close()

    @staticmethod
    async def getall(
        cog: "Servers", command: str = f"SELECT GuildID FROM {DB};", args: Union[list, tuple] = ()
    ) -> List["Server"]:
        async with cog.pool.acquire() as conn:
            cursor = await conn.cursor()

            await cursor.execute(command, args)
            servers = [
                await cog.from_guild(cog, cog.bot.get_guild(guild_id), cursor)
                for guild_id in map(lambda rows: rows[0], await cursor.fetchall())
            ]

            await cursor.close()

        return servers

    @staticmethod
    async def getall_bytime(
        cog: "Servers", before: float = 0, after: float = None, limit: int = 15
    ) -> List["Server"]:
        if after is None:
            after = time()

        return await cog.getall(
            cog, f"""--sql
            SELECT GuildID FROM {DB}
            ORDER BY RaiseTime DESC
            WHERE RaiseTime > %s AND RaiseTime <= %s
            LIMIT %s;""", (before, after, limit)
        )