# RT - NG Word

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseLocker
from rtutil.SettingAPI import *
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

    async def show_ngwords(self, ctx, item):
        if mode == "read":
            item.text = "\n".join(await self.get(ctx.guild.id))
            item.multiple_line = True
            return item

    @commands.group(
        aliases=["えぬじーわーど", "ng"],
        extras={
            "setting": SettingData(
                "guild", {"ja": "NGワードのリストです。", "en": "NG word list."}, show_ngwords,
                TextBox("item1", {"ja": "NGワードリスト", "en": "NGWords"}, ""),
                permissions=[]
            )
        }
    )
    async def ngword(self, ctx):
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                title={"ja": "NGワードリスト", "en": "NG Words"},
                description=", ".join(await self.get(ctx.guild.id)),
                color=self.bot.colors["normal"]
            )
            await ctx.reply(embed)

    async def add_ngword(self, ctx, item):
        # NGワードを追加する。
        if ctx.mode == "read":
            return item
        else:
            for word in item.text.splitlines():
                try:
                    await self.add(ctx.guild.id, word)
                except ValueError:
                    pass

    @ngword.command(
        name="add", aliases=["あどど"], extras={
            "setting": SettingData(
                "guild", {"ja": "NGワードの登録ができます。改行で複数登録できます。", "en": "..."},
                add_ngword,
                TextBox("item1", {
                        "ja": "NGワード登録ボックス", "en": "NGWords registration"
                    }, ""),
                permissions=["manage_messages"]
            )
        }
    )
    @commands.has_permissions(manage_messages=True)
    async def add_(self, ctx, *, words):
        await self.add_ngword(
            Context("write", ctx.author),
            TextBox("item1", "", words)
        )
        await ctx.send(f"{ctx.author.mention}, Ok", replace_language=False)

    async def remove_ngword(self, ctx, item):
        # NGワードを削除する。
        if ctx.mode == "read":
            return item
        else:
            for word in item.text.splitlines():
                try:
                    await self.remove(ctx.guild.id, word)
                except ValueError:
                    SettingAPI.error(f"{word}が見つかりませんでした。 / Not found {word}.")

    @ngword.command(
        name="remove", aliases=["りむーぶ", "rm", "delete", "del"],
        extras={
            "setting": SettingData(
                "guild", {"ja": "NGワードの削除ができます。改行で複数登録できます。", "en": "..."},
                remove_ngword,
                TextBox("item1", {
                        "ja": "NGワード削除ボックス", "en": "Remove ngwords"
                    }, ""),
                permissions=["manage_messages"]
            )
        }
    )
    @commands.has_permissions(manage_messages=True)
    async def remove_(self, ctx, *, words):
        await self.remove_ngword(
            Context("write", ctx.author),
            TextBox("item1", "", words)
        )
        await ctx.send(f"{ctx.author.mention}, Ok", replace_language=False)

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
