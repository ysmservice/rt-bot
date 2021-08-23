# RT - Captcha

from discord.ext import commands
import discord

from rtlib import DatabaseLocker, mysql


class DataManager(DatabaseLocker):
    def __init__(self, db: mysql.MySQLManager):
        self.db: mysql.MySQLManager = db

    async def init_table(self):
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(
                "captcha", {
                    "GuildID": "BIGINT",
                    "ChannelID": "BIGINT",
                    "Mode": "TEXT",
                    "RoleID": "BIGINT",
                    "Extras": "TEXT"
                }
            )


class Captcha(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()