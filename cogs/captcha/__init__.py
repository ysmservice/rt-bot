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

    async def save(self, channel: discord.TextChannel, mode: str,
                   role_id: int, extras: dict) -> None:
        async with self.db.get_cursor() as cursor:
            target = {"GuildID": channel.guild.id}
            if await cursor.exists("captcha", target):
                await cursor.delete("captcha", target)
            target.update({"ChannelID": channel.id, "Mode": mode,
                           "RoleID": role_id, "Extras": extras})
            await cursor.insert("captcha", target)

    async def load(self, guild_id: int) -> tuple:
        async with self.db.get_cursor() as cursor:
            target = {"GuildID": guild_id}
            if await cursor.exists("captcha", target):
                if (row := await cursor.get_data("captcha", target)):
                    return row
            return ()


class Captcha(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()


def setup(bot):
    return
    bot.add_cog(Captcha(bot))