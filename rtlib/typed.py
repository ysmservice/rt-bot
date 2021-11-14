# RT Lib - Typed

from typing import List

from discord.ext import commands

from aiohttp import ClientSession
from aiomysql import Pool

from .mysql_manager import MySQLManager
from data import data, Colors, is_admin


class RT(commands.AutoShardedBot):
    mysql: MySQLManager
    pool: Pool
    test: bool
    data: data
    admins: List[int]
    session: ClientSession
    secret: dict
    is_admin: is_admin
    colors: dict
    Colors: Colors

    def print(self, *args, **kwargs) -> None:
        return print(f"[Backend]", *args, **kwargs)

    def get_ip(self) -> str:
        return "localhost" if self.test else "146.59.153.178"

    def get_url(self) -> str:
        origin = self.get_ip()
        return f"http{'s' if origin[0] == 'r' else ''}://{origin}"

    async def close(self) -> None:
        self.print("Closing...")
        self.dispatch("close", self.loop)
        await super().close()
        self.print("Bye")