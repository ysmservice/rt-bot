# RT.Guilds - Data Manager

from typing import TYPE_CHECKING

from rtutil import DatabaseManager

from .constants import TABLES

if TYPE_CHECKING:
    from aiomysql import Pool, Cursor
    from .__init__ import Guilds


class DataManager(DatabaseManager):
    def __init__(self, cog: "Guilds"):
        self.cog = cog
        self.pool: "Pool" = cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self, cursor: "Cursor" = ...):
        # テーブルを作成します。このクラスのインスタンスの作成時に自動で実行されます。
        await cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {TABLES[0]} (
                GuildID BIGINT PRIMARY KEY NOT NULL, RaiseTime
            );"""
        )