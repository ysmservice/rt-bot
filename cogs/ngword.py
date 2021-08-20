# RT - NG Word

from discord.ext import commands
import discord

from rtutil import SettingManager
from typing import List
from rtlib import mysql


class DataManager:
    def __init__(self, db: mysql.MySQLManager):
        self.db: mysql.MySQLManager = db

    async def init_table(self) -> None:
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(
                "ngword", {"id": "BIGINT", "word": "TEXT"}
            )

    async def get(self, guild_id: int) -> List[str]:
        async with self.db.get_cursor() as cursor:
            rows = await cursor.get_datas("ngword", {"id": guild_id})
            if rows:
                return [row[-1] for row in rows]
            else:
                return []

    async def exists(self, guild_id: int) -> bool:
        async with self.db.get_cursor() as cursor:
            return await cursor.exists("ngword", {"id": guild_id})

    async def add(self, guild_id: int, word: str) -> None:
        async with self.db.get_cursor() as cursor:
            values = {"word": word, "id": guild_id}
            if await cursor.exists("ngword", values):
                raise ValueError("すでに追加されています。")
            else:
                await cursor.insert_data("ngword", values)

    async def remove(self, guild_id: int, word: str) -> None:
        async with self.db.get_cursor() as cursor:
            targets = {"id": guild_id, "word": word}
            if await cursor.exists("ngword", targets):
                await cursor.delete("ngword", targets)
            else:
                raise ValueError("そのNGワードはありません。")


class NgWord(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        super(DataManager, self).__init__(self.bot.data["mysql"])

    @commands.group(aliases=["えぬじーわーど"])
    async def ngword(self, ctx):
        if not ctx.invoked_subcommand:
            words = await self.get(ctx.guild.id)
            embed = discord.Embed(
                title={"ja": "NGワードリスト", "en": "NG Words"},
                description=", ".join(words),
                color=self.bot.colors["normal"]
            )
            await ctx.reply(embed)

    async def add_ngword(self, ctx, mode, items):
        # NGワードを追加する。
        if mode == "read":
            words = await self.get(ctx.guild.id)
            yield {"text": "\n".join(words), "multiple": True}
        else:
            _, item = items
            for word in item["text"].splitlines():
                try:
                    await self.add(ctx.guild.id, word)
                except ValueError:
                    pass

    @SettingManager.setting(
        "guild", "NG Word",
        {"ja": "NGワードの追加をします。", "en": "..."},
        ["manage_messages"], add_ngword, {"text:text": "NGワードリスト"}
    )
    @ngword.command(name="add", aliases=["あどど"])
    @commands.has_permissions(manage_messages=True)
    async def add_(self, ctx, *, words):
        await self.add_ngword(ctx, "write", (0, {"text": words}))


def setup(bot):
    bot.add_cog(NgWord(bot))