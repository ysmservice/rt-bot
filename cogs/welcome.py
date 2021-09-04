# RT - Welocme Message

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseManager
from asyncio import sleep


class DataManager(DatabaseManager):

    DB = "Welcome"

    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.DB, {
                "GuildID": "BIGINT", "ChannelID": "BIGINT",
                "Content": "TEXT"
            }
        )

    async def write(self, cursor, guild_id: int, channel_id: int, content: str) -> None:
        target = {"GuildID": guild_id}
        change = {"ChannelID": channel_id, "Content": content}
        if await cursor.exists(self.DB, target):
            await cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await cursor.insert_data(self.DB, target)

    async def delete(self, cursor, guild_id: int) -> None:
        target = {"GuildID": guild_id}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)
        else:
            raise KeyError("そのサーバーは設定していません。")

    async def read(self, cursor, guild_id: int) -> tuple:
        target = {"GuildID": guild_id}
        if await cursor.exists(self.DB, target):
            return await cursor.get_data(self.DB, target)
        else:
            return ()


class Welcome(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()

    @commands.command(
        aliases=["wm", "ようこそ"], extras={
            "headding": {
                "ja": "ウェルカムメッセージ",
                "en": "Welcome message"
            }, "parent": "ServerTool"
        }
    )
    @commands.cooldown(1, 8, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx, *, content):
        """!lang ja
        --------
        ウェルカムメッセージを設定します。  
        このコマンドを実行したチャンネルにメンバーがサーバーに参加した際に指定したメッセージが送信されるようになります。

        Parameters
        ----------
        content : str
            ウェルカムメッセージの内容です。

        Notes
        -----
        以下の三つをメッセージ内に置けばそれに対応するものにメッセージ送信時に置き換えます。  
        これを使えば`XX人目の参加者です！`のようなメッセージを作ることができます。
        ```
        $ment$ 参加者のメンション
        $name$ 参加者の名前
        $count$ サーバーにいる人の人数
        ```

        Examples
        --------
        ```
        rt!welcome $ment$, ようこそ！RTサーバーへ！！
        あなたは$count$人目の参加者です。
        ```

        Aliases
        -------
        wm, ようこそ

        !lang en
        --------
        Sets the welcome message.  
        When a member joins the server on the channel where this command is executed, the specified message will be sent.

        Parameters
        ----------
        content : str
            The content of the welcome message.

        Notes
        -----
        If you put the following three in your message, it will be replaced by the corresponding one when you send the message.  
        You can use this to create a message like `You are the XXth person to join! You can use this to create a message such as:
        ````
        $ment$ Participant's Mention
        $name$ Participant's name
        $count$ Number of people on the server.
        ```

        Examples
        --------
        ```
        rt!welcome $ment$, Welcome to the RT server!
        You are the $count$th participant.
        Welcome to the RT server!
        ```

        Aliases
        -------
        wm"""
        if content.lower() in ("off", "false", "disable", "0"):
            try:
                await self.delete(ctx.guild.id)
            except KeyError:
                await ctx.reply(
                    {"ja": "まだ設定されていません。",
                     "en": "Welcome has not set yet."}
                )
            else:
                await ctx.reply("Ok")
        else:
            await self.write(ctx.guild.id, ctx.channel.id, content)
            await ctx.reply("Ok")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.bot.is_ready():
            if (row := await self.read(member.guild.id)):
                row[2] = (row[2]
                    .replace("$ment$", member.mention)
                    .replace("$name$", member.name)
                    .replace("$count$", str(len(member.guild.members))))
                channel = member.guild.get_channel(row[1])
                if channel:
                    await sleep(1.5)
                    await channel.send(row[2])


def setup(bot):
    bot.add_cog(Welcome(bot))
