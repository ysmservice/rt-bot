# RT - Stamp

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseLocker
from typing import Optional


class DataManager(DatabaseLocker):

    DB = "Stamp"

    def __init__(self, db):
        self.db = db
        self.auto_cursor = True

    async def init_table(self) -> None:
        await self.cursor.create_table(
            self.DB, {
                "GuildID": "BIGINT", "Name": "TEXT", "Url": "TEXT"
            }
        )

    async def write(self, guild_id: int, name: str, url: str) -> None:
        target = {"GuildID": guild_id, "Name": name}
        change = {"Url": url}
        if await self.cursor.exists(self.DB, target):
            await self.cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await self.cursor.insert_data(self.DB, target)

    async def delete(self, guild_id: int, name: str) -> None:
        target = {"GuildID": "BIGINT", "Name": name}
        if await self.cursor.exists(self.DB, target):
            await self.cursor.delete(self.DB, target)
        else:
            raise KeyError("そのスタンプが見つかりませんでした。")

    async def read(self, guild_id: int) -> Optional[tuple]:
        target = {"GuildID": guild_id}
        if await self.cursor.exists(self.DB, target):
            return [
                row
                async for row in self.cursor.get_datas(
                    self.DB, target
                )
            ]

    async def reads(self) -> list:
        return [row async for row in self.cursor.get_datas(self.DB, {})]


class Stamp(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    @commands.Cog.listener()
    async def on_ready(self):
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()
        await self.update_cache()

    async def update_cache(self, guild_id: Optional[int] = None) -> None:
        for row in (
                await self.read(guild_id)
                if guild_id
                else await self.reads()
            ):
            if row:
                if row[0] not in self.cache:
                    self.cache[row[0]] = {}
                self.cache[row[0]][row[1]] = row[2]

    @commands.group(
        aliases=["sp", "スタンプ", "すたんぷ"], extras={
            "headding": {
                "ja": "スタンプ機能", "en": "Stamp function"
            }, "parent": "ServerUseful"
        }
    )
    async def stamp(self, ctx):
        """!lang ja
        --------
        スタンプ機能です。  
        指定した名前をメッセージに含めて送信すると指定した画像が送信されるというものです。

        Aliases
        -------
        sp, すたんぷ, スタンプ

        !lang en
        --------
        Stamp function.  
        When you send a message with a specified name, the specified image will be sent.

        Aliases
        -------
        sp"""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    title="Stamp List",
                    description=", ".join(
                        f"[{key}]({self.cache[ctx.guild.id][key]})"
                        for key in self.cache.get(ctx.guild.id, {})
                    ),
                    color=self.bot.colors["normal"]
                )
            )

    @stamp.command("set", aliases=["せっと"])
    async def set_stamp(self, ctx, *, name):
        """!lang ja
        --------
        スタンプを設定します。

        Parameters
        ----------
        name : str
            スタンプの名前です。  
            `thx!`にすればコマンド実行時に添付したファイルを`thx!`が含まれたメッセージが送信された際に送信します。

        Aliases
        -------
        せっと

        !lang en
        --------
        Sets the stamp.

        Parameters
        ----------
        name : str
            The name of the stamp.  
            If set to `thx!`, the attached file will be sent when the command is executed and the message containing `thx!` is sent."""
        if ctx.message.attachments:
            if len(self.cache.get(ctx.guild.id, ())) == 50:
                await ctx.reply(
                    {"ja": "50個以上登録することはできません。",
                     "en": "You can't register more than 50 stamps."}
                )
            else:
                await self.write(
                    ctx.guild.id, name,
                    ctx.message.attachments[0].url
                )
                await self.update_cache(ctx.guild.id)
                await ctx.reply("Ok")
        else:
            await ctx.reply(
                {"ja": "画像を添付してください。",
                 "en": "Please attach the image."}
            )

    @stamp.command(
        "delete",
        aliases=["rm", "remove", "del", "さくじょ", "削除"]
    )
    async def delete_stamp(self, ctx, *, name):
        """!lang ja
        --------
        設定したスタンプを削除します。

        Parameters
        ----------
        name : str
            スタンプの名前です。

        Aliases
        -------
        rm, remove, del, さくじょ, 削除

        !lang en
        --------
        Deletes the set stamp.

        Parameters
        ----------
        name : str
            The name of the stamp.

        Aliases
        -------
        rm, remove, del"""
        if name in self.cache.get(ctx.guild.id, {}):
            await self.delete(ctx.guild.id, name)
            await self.update_cache(ctx.guild.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply(
                {"ja": "そのスタンプは登録されていません。",
                 "en": "The stamp has not registered yet."}
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (message.guild and not message.author.bot
                and (data := self.cache.get(message.guild.id))
                and not message.content.startswith(
                    tuple(self.bot.command_prefix)
                )
            ):
            for name in data:
                if name in message.content:
                    await message.channel.send(data[name])
                    break


def setup(bot):
    bot.add_cog(Stamp(bot))