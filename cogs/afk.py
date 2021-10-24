# RT - AFK

from typing import TYPE_CHECKING, TypedDict, Literal, Union, Dict

from discord.ext import commands
import discord

from ujson import loads, dumps

if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


TABLES = ("AFK", "AFKAuto")
DEFAULT_CONTENT = "None"
DEFAULT_MAX_AUTO = 15
ALLOW_DAY_OF_WEEK = ("月", "火", "水", "木", "金", "土", "日")


class DataManager:
    def __init__(self, cog: "AFK"):
        self.cog = cog
        self.pool: "Pool" = self.cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {TABLES[0]} (
                        UserID BIGINT PRIMARY KEY NOT NULL, Content TEXT
                    );"""
                )
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {TABLES[1]} (
                        UserID BIGINT, Content TEXT, Data JSON
                    );"""
                )

    async def get_data(self, user: discord.User) -> "UserData":
        """データクラスを取得します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT Content FROM {TABLES[0]} WHERE UserID = %s;",
                    (user.id,)
                )
                kwargs = {"pool": self.pool, "user": user, "autos": {}}
                if (row := await cursor.fetchone()):
                    kwargs["content"] = row[1]
                await cursor.execute(
                    f"SELECT Name, Data FROM {TABLES[1]} WHERE UserID = %s;",
                    (user.id,)
                )
                for row in await cursor.fetchall():
                    if row:
                        kwargs["autos"][row[0]] = loads(row[1])
                return UserData(**kwargs)


class AutoData(TypedDict, total=False):
    content: str
    mode: Literal["time", "cmd"]
    day_of_week: Union[ALLOW_DAY_OF_WEEK]
    time: str


class UserData:
    def __init__(
        self, pool: "Pool", user: discord.User,
        content: str = DEFAULT_CONTENT,
        autos: Dict[str, AutoData] = {}
    ):
        self.pool, self.user, self.content, self.autos = pool, user, content, autos

    async def setting(self, content: str) -> None:
        """AFKを設定します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {TABLES[0]} VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE Content = %s;""",
                    (self.user.id, content, content)
                )
        self.content = content

    async def auto(self, name: str, data: AutoData) -> None:
        """自動でAFKを設定するようにします。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert len(self.autos) < DEFAULT_MAX_AUTO, "これ以上は設定できません。"
                await cursor.execute(
                    f"INSERT INTO {TABLES[1]} VALUES (%s, %s, %s);",
                    (self.user.id, name, dumps(data))
                )
                self.autos[name] = data

    async def remove(self, name: str) -> None:
        """自動でAFKを設定する設定を削除します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert name in self.autos, "その設定はありません。"
                await cursor.execute(
                    f"DELETE FROM {TABLES[1]} WHERE UserID = %s AND Name = %s;",
                    (self.user.id, name)
                )
                del self.autos[name]


class AFK(commands.Command, DataManager):
    def __init__(self, bot: "Backend"):
        self.bot = bot