# RT - NG Word

from discord.ext import commands
import discord

from rtlib import mysql


class DataManager:
    def __init__(self, db: mysql.MySQLManager):
        self.db: mysql.MySQLManager = db

    async def init_table(self) -> None:
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(
                "ngword", {"id": "BIGINT", "data": "TEXT"}
            )

    async def get(self, guild_id: int) -> dict:
        async with self.db.get_cursor() as cursor:
            rows = await cursor.get_data("ngword", {"id": guild_id})
            if rows:
                return rows[-1]
            else:
                return {}

    async def exists(self, guild_id: int) -> bool:
        async with self.db.get_cursor() as cursor:
            return await cursor.exists("ngword", {"id": guild_id})

    async def set_data(self, guild_id: int, data: dict) -> None:
        async with self.db.get_cursor() as cursor:
            values = {"data": data}
            targets = {"id": guild_id}
            if await self.exists(guild_id):
                await cursor.update_data("ngword", values, targets)
            else:
                targets.update(values)
                await cursor.insert_data("ngword", values)


class NgWord(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=["えぬじーわーど"])
    async def ngword(self, ctx):
        pass


def setup(bot):
    bot.add_cog(NgWord(bot))