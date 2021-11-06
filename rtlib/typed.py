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