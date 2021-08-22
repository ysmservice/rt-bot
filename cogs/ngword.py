# RT - NG Word

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseLocker
from rtutil import SettingManager
from typing import List


class DataManager(DatabaseLocker):
    def __init__(self, db: mysql.MySQLManager):
        self.db: mysql.MySQLManager = db

    async def init_table(self) -> None:
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(
                "ngword", {"id": "BIGINT", "word": "TEXT"}
            )

    async def get(self, guild_id: int) -> List[str]:
        async with self.db.get_cursor() as cursor:
            return [row[-1] async for row in cursor.get_datas(
                "ngword", {"id": guild_id}) if row]

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

    @commands.Cog.listener()
    async def on_ready(self):
        self.db = await self.bot.mysql.get_database()
        super(commands.Cog, self).__init__(self.db)
        await self.init_table()

    async def show_ngwords(self, ctx, mode, items):
        if mode == "read":
            yield {"text": "\n".join(await self.get(ctx.guild.id)), "multiple": True}

    @SettingManager.setting(
        "guild", "Add NG Word",
        {"ja": "現在登録されているNGワードのリストです。\nここから設定変更はできません。",
         "en": "..."},
        [], show_ngwords,
        {"text:text": {"ja": "NGワードリスト", "en": "NG Word list"}}
    )
    @commands.group(aliases=["えぬじーわーど", "ng"])
    async def ngword(self, ctx):
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                title={"ja": "NGワードリスト", "en": "NG Words"},
                description=", ".join(await self.get(ctx.guild.id)),
                color=self.bot.colors["normal"]
            )
            await ctx.reply(embed)

    async def add_ngword(self, ctx, mode, items):
        # NGワードを追加する。
        if mode == "read":
            yield {"text": "", "multiple": True}
        else:
            _, item = items
            for word in item["text"].splitlines():
                try:
                    await self.add(ctx.guild.id, word)
                except ValueError:
                    pass
            yield None

    @SettingManager.setting(
        "guild", "Add NG Word",
        {"ja": "NGワードの追加をします。\n改行することで複数登録できます。",
         "en": "..."},
        ["manage_messages"], add_ngword,
        {"text:text": {"ja": "NGワード", "en": "NG Words"}}
    )
    @ngword.command(name="add", aliases=["あどど"])
    @commands.has_permissions(manage_messages=True)
    async def add_(self, ctx, *, words):
        await self.add_ngword(ctx, "write", (0, {"text": words})).__anext__()
        await ctx.reply("Ok")

    async def remove_ngword(self, ctx, mode, items):
        # NGワードを削除する。
        if mode == "read":
            yield {"text": "", "multiple": True}
        else:
            _, item = items
            for word in item["text"].splitlines():
                try:
                    await self.remove(ctx.guild.id, word)
                except ValueError:
                    yield {"ja": f"{word}というNGワードが見つかりませんでした。",
                           "en": "..."}
            yield None

    @SettingManager.setting(
        "guild", "Remove NG Word",
        {"ja": "NGワードの削除をします。\n改行することで複数選択が可能です。",
         "en": "..."},
        ["manage_messages"], add_ngword,
        {"text:text": {"ja": "NGワードリスト", "en": "NG Word List"}}
    )
    @ngword.command(name="remove", aliases=["りむーぶ", "rm", "delete", "del"])
    @commands.has_permissions(manage_messages=True)
    async def remove_(self, ctx, *, words):
        callback = await SettingManager.anext(
            self.remove_ngword(ctx, "write", (0, {"text": words})), None
        )
        if callback is None:
            await ctx.reply("Ok")
        else:
            await ctx.reply(callback)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 関係ないメッセージは無視する。
        if not message.guild:
            return

        if getattr(message.author, "guild_permissions.administrator", True):
            for word in await self.get(message.guild.id):
                if word in message.content:
                    await message.delete()
                    await message.channel.send(
                        embed=discord.Embed(
                            title={"ja": "NGワードを削除しました。",
                                   "en": "..."},
                            description=(f"Author:{message.author.mention}\n"
                                         f"Content:||{message.content}||"),
                            color=self.bot.colors["unknown"]
                        ), target=(message.guild.owner or message.author).id
                    )
                    break


def setup(bot):
    bot.add_cog(NgWord(bot))
