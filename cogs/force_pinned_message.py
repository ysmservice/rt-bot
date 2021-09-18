# RT - Force Pinned Message

from discord.ext import commands, tasks
import discord

from typing import Tuple, Dict, List
from rtlib import DatabaseManager
from ujson import loads, dumps


class DataManager(DatabaseManager):

    TABLE = "ForcePinnedMessage"

    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.TABLE, dict(
                GuildID="BIGINT", ChannelID="BIGINT", AuthorID="BIGINT",
                MessageID="BIGINT", Bool="TINYINT", Text="TEXT"
            )
        )

    async def setting(
            self, cursor, guild_id: int, channel_id: int, message_id: int,
            author_id: int, onoff: bool, text: str) -> None:
        value = dict(Bool=int(onoff), Text=text,
                     AuthorID=author_id, MessageID=message_id)
        target = dict(GuildID=guild_id, ChannelID=channel_id)
        if await cursor.exists(self.TABLE, target):
            await cursor.update_data(self.TABLE, value, target)
        else:
            value.update(target)
            await cursor.insert_data(self.TABLE, value)

    async def get(self, cursor, guild_id: int, channel_id: int) -> Tuple[int, int, bool, str]:
        target = dict(GuildID=guild_id, ChannelID=channel_id)
        if await cursor.exists(self.TABLE, target):
            if (row := await cursor.get_data(self.TABLE, target)):
                return row[-4], row[-3], bool(row[-2]), row[-1]
            else:
                return 0, 0, False, ""
        else:
            return 0, 0, False, ""


class ForcePinnedMessage(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.queue: Dict[int, discord.Message] = {}
        self.remove_queue: List[int] = []
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        await self.bot.wait_until_ready()
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()
        self.worker.start()

    @commands.command(
        extras={
            "headding": {
                "ja": "いつも下にくるメッセージ。強制ピン留めメッセージ機能。",
                "en": "Messages that always come to the bottom. Force pinned message function."
            },
            "parent": "ServerTool"
        },
        aliases=["ピン留め", "ぴんどめ", "fpm", "forcepinmessage"]
    )
    @commands.has_permissions(manage_messages=True)
    async def pin(self, ctx, onoff: bool, *, content=""):
        """!lang ja
        --------
        いつも下にくるメッセージを作ることができます。  
        メッセージ削除権限を持つ人のみ実行可能です。  
        別名強制ピン留めメッセージです。

        Parameters
        ----------
        onoff : bool
            onにすると強制ピン留めメッセージを作ります。  
            もし強制ピン留めメッセージを無効にした際はこれをoffにしてください。
        content : str
            いつも下にくるメッセージの内容です。  
            onoffをoffにした際はこれは書かなくて良いです。

        Aliases
        -------
        fpm, forcepinmessage, ピン留め, ぴんどめ

        Examples
        --------
        ```
        rt!pin on 自己紹介テンプレート：
        名前：
        性別：
        一言：
        ```

        Notes
        -----
        下に来るメッセージは数秒毎に更新されるので数秒は下に来ないことがあります。  
        以下のように最初に`>>`を置いて`embed`コマンドの構文を使えば埋め込みにすることができます。
        ```
        rt!pin on >>タイトル
        説明
        <フィールド名
        フィールド内容
        ```

        Warnings
        --------
        設定後はすぐに下にこないことがあります。  
        しばらくしても下に来ない際はメッセージを送ってみてください。  
        これはRTがメッセージを送りすぎてAPI制限になるということを防止するために発生するものでご了承ください。

        !lang en
        --------
        You can create a message that always comes at the bottom.  
        This can only be done by someone with the Delete Message permission.  
        Also known as a force pinned message.

        Parameters
        ----------
        onoff : bool
            When set to "on", this function creates a forced pinning message.  
            If you want to disable the forced pinning message, set this to off.
        content : str
            The content of the message that always appears below.  
            If you turn off onoff, you do not need to write this.

        Aliases
        -------
        fpm, forcepinmessage

        Examples
        --------
        ```
        rt!pin on Self-introduction template:
        Name:
        Gender:
        Comment:
        ```

        Warnings
        --------
        After setting it up, it may not come down immediately.  
        If it doesn't come down after a while, please try sending a message.  
        Please note that this is to prevent RTs from sending too many messages, which would limit the API."""
        if hasattr(ctx.channel, "topic"):
            await ctx.trigger_typing()
            if content.startswith(">>"):
                content = "<" + dumps(
                    self.bot.cogs["ServerTool"].easy_embed(
                        content, ctx.author.color
                    ).to_dict()
                ) + ">"
            await self.setting(
                ctx.guild.id, ctx.channel.id, 0,
                ctx.author.id, onoff, content
            )
            if not onoff and ctx.channel.id in self.queue:
                del self.queue[ctx.channel.id]
                if ctx.channel.id not in self.remove_queue:
                    self.remove_queue.append(ctx.channel.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply("スレッドに設定することはできません。")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or "RT-" in message.author.name or not self.bot.is_ready():
            return

        if message.channel.id not in self.remove_queue:
            fpm = await self.get(message.guild.id, message.channel.id)
            if fpm[2]:
                self.queue[message.channel.id] = (message, fpm)

    def cog_unload(self):
        self.worker.cancel()

    @tasks.loop(seconds=5)
    async def worker(self):
        for channel_id in list(self.queue.keys()):
            if channel_id in self.remove_queue:
                self.remove_queue.remove(channel_id)
            message, fpm = self.queue[channel_id]
            new_message = None
            try:
                if fpm[1] != 0:
                    # 前回のメッセージの削除を試みる。
                    before_message = await message.channel.fetch_message(fpm[1])

                    if before_message:
                        await before_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
            try:
                del self.queue[channel_id]
            except KeyError:
                pass

            member = message.guild.get_member(fpm[0])
            content = fpm[3]
            if content.startswith("<") and content.endswith(">"):
                try:
                    kwargs = {"embed": discord.Embed.from_dict(loads(content[1:-1]))}
                except ValueError:
                    kwargs = {"content": content}
            else:
                kwargs = {"content": content}

            try:
                new_message = await message.channel.webhook_send(
                    username=f"{member.display_name} RT-ForcePinnedMessage",
                    avatar_url=member.avatar.url, wait=True
                    **kwargs
                )
            except Exception as e:
                print("(ignore) Error on ForcePinnedMessage:", e)

            await self.setting(
                message.guild.id, message.channel.id,
                getattr(new_message, "id", 0),
                member.id, True, fpm[3]
            )


def setup(bot):
    bot.add_cog(ForcePinnedMessage(bot))
