# RT - NG Word

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseManager
from rtutil.SettingAPI import *
from typing import List


class DataManager(DatabaseManager):
    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            "ngword", {"id": "BIGINT", "word": "TEXT"}
        )

    async def get(self, cursor, guild_id: int) -> List[str]:
        return [
            row[-1] async for row in cursor.get_datas(
            "ngword", {"id": guild_id}) if row
        ]

    async def exists(self, cursor, guild_id: int) -> bool:
        return await cursor.exists("ngword", {"id": guild_id})

    async def add(self, cursor, guild_id: int, word: str) -> None:
        values = {"word": word, "id": guild_id}
        if await cursor.exists("ngword", values):
            raise ValueError("すでに追加されています。")
        else:
            await cursor.insert_data("ngword", values)

    async def remove(self, cursor, guild_id: int, word: str) -> None:
        targets = {"id": guild_id, "word": word}
        if await cursor.exists("ngword", targets):
            await cursor.delete("ngword", targets)
        else:
            raise ValueError("そのNGワードはありません。")


class NgWord(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(commands.Cog, self).__init__(self.bot.mysql)
        await self.init_table()

    async def show_ngwords(self, ctx, item):
        if ctx.mode == "read":
            item.text = "\n".join(await self.get(ctx.guild.id))
            item.multiple_line = True
            return item

    @commands.group(
        aliases=["えぬじーわーど", "ng"], extras={
            "headding": {"ja": "NGワード", "en": "NG Word"},
            "parent": "ServerSafety"
        }
    )
    async def ngword(self, ctx):
        """!lang ja
        --------
        NGワード機能です。

        !lang en
        --------
        NG Word feature."""
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                title={"ja": "NGワードリスト", "en": "NG Words"},
                description=", ".join(await self.get(ctx.guild.id)),
                color=self.bot.colors["normal"]
            )
            await ctx.reply(embed=embed)

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
        name="add", aliases=["あどど"]
    )
    @commands.has_permissions(manage_messages=True)
    async def add_(self, ctx, *, words):
        """!lang ja
        --------
        NGワードを追加します。

        Parameters
        ----------
        words : NGワード(複数)
            空白を使うことで複数一括で登録できます。

        Examples
        --------
        `rt!ngword add あほー`

        !lang en
        --------
        Add NG words.

        Parameters
        ----------
        words : NG word(s)
            You can add multiple words at once by using a blank space.

        Examples
        --------
        `rt!ngword add Ahoy! Idiot`"""
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
        name="remove", aliases=["りむーぶ", "rm", "delete", "del"]
    )
    @commands.has_permissions(manage_messages=True)
    async def remove_(self, ctx, *, words):
        """!lang ja
        --------
        NGワードを削除します。  
        NGワードを追加する際に実行したコマンドの逆です。

        Examples
        --------
        `rt!ngword remove みすった NGワード`

        !lang en
        --------
        Remove the ng word(s).  
        This is the reverse of the command you executed when registering NG words.

        Examples
        --------
        `rt!ngword remove Badngword"""
        await self.remove_ngword(
            Context("write", ctx.author),
            TextBox("item1", "", words)
        )
        await ctx.send(f"{ctx.author.mention}, Ok", replace_language=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 関係ないメッセージは無視する。
        if not message.guild or not self.bot.is_ready():
            return

        if getattr(message.author, "guild_permissions.administrator", True):
            for word in await self.get(message.guild.id):
                if word in message.content:
                    await message.delete()
                    await message.channel.send(
                        embed=discord.Embed(
                            title={"ja": "NGワードを削除しました。",
                                   "en": "Removed the NG Word."},
                            description=(f"Author:{message.author.mention}\n"
                                         f"Content:||{message.content}||"),
                            color=self.bot.colors["unknown"]
                        ), target=(message.guild.owner or message.author).id
                    )
                    break


def setup(bot):
    bot.add_cog(NgWord(bot))
