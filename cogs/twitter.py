# RT - Twitter

from typing import TYPE_CHECKING, Tuple, List

from discord.ext import commands
import discord

from tweepy.asynchronous import AsyncStream

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from aiomysql import Pool
    from rtlib import Backend


class DataManager:

    TABLE = "TwitterNotification"

    def __init__(self, loop: "AbstractEventLoop", pool: "Pool"):
        self.pool = pool

    async def _prepare_table(self):
        # テーブルを準備します。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                        GuildID BIGINT, ChannelID BIGINT, UserName TEXT
                    );"""
                )

    async def write(self, channel: discord.TextChannel, username: str) -> None:
        "設定を保存します。"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {self.TABLE} WHERE ChannelID = %s AND UserName = %s;",
                    (channel.id, username)
                )
                assert not await cursor.fetchone(), "既に設定されています。"
                await cursor.execute(
                    f"INSERT INTO {self.TABLE} VALUES (%s, %s, %s);",
                    (channel.guild.id, channel.id, username)
                )

    async def reads(self) -> List[Tuple[int, str]]:
        "設定を読み込みます。"
        pass