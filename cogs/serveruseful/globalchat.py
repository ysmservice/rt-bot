# Free RT - Global Chat
import io
import os
import sys
from urllib.parse import urlparse
import aiohttp
import ygclib
import ujson
from typing import TYPE_CHECKING, Optional

from discord.ext import commands
from discord import app_commands
import discord

from collections import defaultdict
from util.mysql_manager import DatabaseManager
from functools import wraps
from time import time

if TYPE_CHECKING:
    from util import Backend
    from discord.types.message import Message as MessageType ,Attachment as AttachmentPayload


class DataManager(DatabaseManager):
    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            "globalChat", {
                "Name": "TEXT", "ChannelID": "BIGINT",
                "Extras": "JSON"
            }
        )

    async def load_globalchat_name(self, cursor, channel_id: int) -> list:
        target = {"ChannelID": channel_id}
        if await cursor.exists("globalChat", target):
            return await cursor.get_data("globalChat", target)
        else:
            return ()

    async def load_globalchat_channels(self, cursor, name: str) -> list:
        target = {"Name": name}
        if await cursor.exists("globalChat", target):
            return [
                data
                async for data in cursor.get_datas(
                    "globalChat", target
                )
            ]
        else:
            return []

    async def make_globalchat(self, cursor, name: str, channel_id: int, extras: dict) -> None:
        target = {"Name": name, "ChannelID": channel_id, "Extras": extras}
        if await cursor.exists("globalChat", {"Name": name}):
            raise ValueError("既に追加されています。")
        else:
            await cursor.insert_data("globalChat", target)

    async def connect_globalchat(self, cursor, name: str, channel_id: int, extras: dict) -> None:
        target = {"Name": name, "ChannelID": channel_id}
        if await cursor.exists("globalChat", target):
            raise ValueError("既に接続しています。")
        else:
            target["Extras"] = extras
            await cursor.insert_data("globalChat", target)

    async def disconnect_globalchat(self, cursor, name: str, channel_id: int) -> None:
        target = {"Name": name, "ChannelID": channel_id}
        if await cursor.exists("globalChat", target):
            await cursor.delete("globalChat", target)
        else:
            raise ValueError(
                "そのグローバルチャットは存在していないまたはチャンネルは接続していません。"
            )

    async def exists_globalchat(self, cursor, name: str) -> bool:
        return await cursor.exists("globalChat", {"Name": name})

    async def update_extras(self, cursor, name: str, extras: dict) -> None:
        target = {"Name": name}
        change = {"Extras": extras}
        if await cursor.exists("globalChat", target):
            await cursor.update("globalChat", change, target)
        else:
            raise ValueError("グローバルチャットが存在しません。")

    async def delete_globalchat(self, cursor, name: str) -> None:
        await cursor.delete("globalChat", {"Name": name})


def require_guild(coro):
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kwargs):
        if ctx.guild:
            return await coro(self, ctx, *args, **kwargs)
        else:
            return await ctx.reply(
                {"ja": "サーバーのみ実行可能です。",
                 "en": "This command can run only server."}
            )
    return new_coro


def require_globalchat(coro):
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kwargs):
        if (row := await self.load_globalchat_name(ctx.channel.id)):
            ctx.row = row
            return await coro(self, ctx, *args, **kwargs)
        else:
            return await ctx.reply(
                {"ja": "このチャンネルはグローバルチャットではありません。",
                 "en": "The channel is not globalchat."}
            )
    return new_coro


class GlobalChat(commands.Cog, DataManager):
    def __init__(self, bot: "Backend"):
        self.bot = bot
        self.blocking = {}
        self.ban_cache = defaultdict(list)
        self.ygc = ygclib.YGC(bot)
        self.share = 707158343952629780
        self.badword = ["discord.gg", "discord.com/invite", "discordapp.net/invite"]

    async def cog_load(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()

    @commands.hybrid_group(
        aliases=["gc", "ぐろちゃ", "ぐろーばるちゃっと"],
        extras={
            "headding": {
                "ja": "グローバルチャット機能",
                "en": "Global chat."
            }, "parent": "ServerUseful"
        }
    )
    async def globalchat(self, ctx):
        """!lang ja
        --------
        グローバルチャット機能です。  
        いくつかのサーバーのチャンネルをRTを経由してつなげることができます。

        Aliases
        -------
        gc, ぐろちゃ, ぐろーばるちゃっと

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    @globalchat.command()
    @commands.has_permissions(administrator=True)
    @require_guild
    @app_commands.describe(name="グローバルチャットの名前")
    async def make(self, ctx, *, name):
        """!lang ja
        --------
        グローバルチャットを作成します。  
        実行したチャンネルが最初のチャンネルとして設定されます。

        Parameters
        ----------
        name : str
            グローバルチャットの名前です。"""
        try:
            await self.make_globalchat(
                name, ctx.channel.id, {"author": ctx.author.id}
            )
        except ValueError:
            await ctx.reply(
                {"ja": "そのグローバルチャットは既に存在します。",
                 "en": "That name is already used."}
            )
        else:
            await ctx.channel.edit(topic="RT-GlobalChat")
            await ctx.reply(
                {"ja": "グローバルチャットを登録しました。",
                 "en": "Success!"}
            )

    @globalchat.command(name="delete", aliases=["del", "rm"])
    @require_guild
    @require_globalchat
    async def delete_(self, ctx):
        """!lang ja
        --------
        実行したチャンネルに設定されているグローバルチャットを削除(全チャンネルの接続の解除)します。  
        グローバルチャット作成者でないと削除はできません。

        Aliases
        -------
        del, rm

        !lang en
        --------
        ..."""
        if ctx.row[-1]["author"] == ctx.author.id:
            await self.delete_globalchat(ctx.row[0])
            await ctx.channel.edit(topic=None)
            await ctx.reply({"ja": "削除しました。", "en": "Success!"})
        else:
            await ctx.reply(
                {"ja": "グローバルチャットの作成者でなければ削除できません。",
                 "en": "You can't delete the global chat because you are not author."}
            )

    @globalchat.command(aliases=["cong", "コネクト", "接続", "せつぞく"])
    @require_guild
    @app_commands.describe(name="グローバルチャットの名前")
    async def connect(self, ctx, *, name="main"):
        """!lang ja
        --------
        グローバルチャットに接続します。

        Parameters
        ----------
        name : str
            グローバルチャットの名前です。

        Aliases
        -------
        cong, コネクト, 接続, せつぞく

        !lang en
        --------
        Connect to global chat.

        Parameters
        ----------
        name : str
            Global chat name.

        Aliases
        -------
        cong"""
        if await self.exists_globalchat(name):
            if ctx.channel.topic and "RT-GlobalChat" in ctx.channel.topic:
                await ctx.reply("既に接続しています。")
            else:
                rows = await self.load_globalchat_channels(name)
                extras = rows[0][-1]
                try:
                    await ctx.channel.edit(topic="RT-GlobalChat")
                except discord.Forbidden:
                    await ctx.reply("権限がないのでチャンネルの編集に失敗しました。")
                else:
                    await self.connect_globalchat(name, ctx.channel.id, extras)
                    await ctx.reply("Ok")
                    # 入室メッセージを送信する。
                    message = ctx.message
                    message.content = f"{ctx.guild.name}がグローバルチャットに参加しました。"
                    await self.send(message, rows[0])
        else:
            await ctx.reply(
                {"ja": "そのグローバルチャットはありません。",
                 "en": "The global chat is not found."}
            )

    @globalchat.command(aliases=["dis", "leave", "bye", "切断", "せつだん"])
    @require_guild
    async def disconnect(self, ctx):
        """!lang ja
        --------
        グローバルチャットから切断します。  

        Aliases
        -------
        dis, leave, bye, 切断, せつだん

        !lang en
        --------
        Disconnect global chat.

        Aliases
        -------
        dis, leave, bye"""
        if (row := await self.load_globalchat_name(ctx.channel.id)):
            await self.disconnect_globalchat(row[0], ctx.channel.id)
            await ctx.channel.edit(topic=None)
            await ctx.reply(
                {"ja": "グローバルチャットから切断しました。",
                 "en": "I have disconnected to global chat."}
            )
        else:
            await ctx.reply(
                {"ja": "ここはグローバルチャットではないです。",
                 "en": "Here is not the global chat."}
            )

    def similer(self, before: str, after: str) -> bool:
        # 文字列がにた文字列かどうかを調べる。
        m = len(before) if len(before) < 6 else 5
        return any(
            after[i:i + m] in before for i in range(len(after) - m)
        )

    async def send(self, message: discord.Message, row: list) -> None:
        # グローバルチャットにメッセージを送る。
        rows = await self.load_globalchat_channels(row[0])

        # もし返信先があるメッセージなら返信先のEmbedを作っておく。
        if message.author.id in (888057396310716496,):
            return
        embeds = []
        if message.reference:
            if hasattr(message.reference, "cached_message1"):
                original = message.reference.cached_message1
            elif message.reference.cached_message:
                original = message.reference.cached_message
            else:
                ch = self.bot.get_channel(message.channel.id)
                original = (
                    await ch.fetch_message(message.reference.message_id)
                    if ch else None
                )

            embeds.append(
                discord.Embed(
                    description=original.clean_content
                ).set_author(
                    name=original.author,
                    icon_url=getattr(original.author.display_avatar, "url", "")
                )
            )

        # スタンプがついているのなら添付ファイルにそのスタンプの画像を添付する。
        if message.stickers:
            for sticker in message.stickers:
                embeds.append(
                    discord.Embed(color=message.author.color)
                    .set_image(url=sticker.url)
                    .set_footer(text="添付されたスタンプ")
                )

        # 送る。
        for _, channel_id, _ in rows:
            if message.channel.id == channel_id:
                continue
            else:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        if channel.guild.id not in self.ban_cache:
                            async for entry in channel.guild.bans():
                                self.ban_cache[channel.guild.id].append(
                                    entry.user.id
                                )
                    except Exception as e:
                        print("Error on global chat :", e)
                    if all(
                        user_id != message.author.id
                        for user_id in self.ban_cache[channel.guild.id]
                    ):
                        try:
                            await channel.webhook_send(
                                username=f"{message.author.name} {message.author.id} (mID:{message.id})",
                                avatar_url=getattr(message.author.display_avatar, "url", ""),
                                content=message.clean_content, embeds=embeds, files=[
                                    await attachment.to_file()
                                    for attachment in message.attachments
                                ]
                            )
                        except Exception as e:
                            print("Error on global chat :", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (not message.guild or isinstance(message.channel, discord.Thread)
                or (not message.channel.topic and not message.channel.id == self.share) or (message.author.bot and not message.channel.id == self.share)
                or ("RT-GlobalChat" not in message.channel.topic and not message.channel.id == self.share)):
            return
        if any(bad_word in message.content for bad_word in self.badword):
            return await message.add_reaction("❎")
        row = await self.load_globalchat_name(message.channel.id)
        mc = ""
        if row or message.channel.id == self.share:
            if message.channel.id == self.share:
                data = ujson.loads(message.content)
                user = int(data["userId"])
                mc = data["content"]
            else:
                user = message.author.id
                mc = message.clean_content
            # スパムの場合は一分停止させる。
            if (before := self.blocking.get(user)):
                if before.get("time", (now := time()) - 1) < now:
                    if self.similer(before["before"], mc):
                        self.blocking[user]["count"] += 1
                        if self.blocking[user]["count"] > 4:
                            self.blocking[user].update(
                                {"time": now + 60}
                            )
                    elif before["count"] > 4:
                        self.blocking[user]["count"] = 0
                else:
                    return await message.add_reaction("❎")
            else:
                self.blocking[user] = {"count": 0}
            self.blocking[user]["before"] = mc
            if message.channel.id == self.share and message.author.id != self.bot.user.id:
                data = ujson.loads(message.content)
                msg1 = await self.create_message(data)
                if "type" in data and data["type"].find("message") == -1:
                    return
                name = "main"
                if data["type"].find("-message-") != -1:
                    name = data["type"].split('-')[-1]
                await self.send(msg1, [name])
                await message.add_reaction("✅")
            elif message.channel.id != self.share:
                sch = self.bot.get_channel(self.share)
                data = ujson.loads(await self.ygc.create_json(message))
                if data["type"].startswith("message"):
                    data.setdefault("reference", "")
                    if data["reference"] != "":
                        data["reference"] = data["reference"]["messageId"]
                    else:
                        data.pop("reference")
                if row[0] == "main":
                    data["type"] = f"message"
                else:
                    data["type"] = f"frt-message-{row[0]}"
                await sch.send(ujson.dumps(data))
                await self.send(message, row)
                await message.add_reaction("✅")

    async def create_message(self, dic: dict, needref = True):
        user = await self.bot.fetch_user(int(dic["userId"]))
        atch = list()
        dic.setdefault("attachmentsUrl",list())
        c = 0
        if dic["attachmentsUrl"] != []:
            for fb in dic["attachmentsUrl"]:
                atch.append(await self.filefromurl(fb,c))
                c = c + 1
        dic.setdefault("embeds", list())
        payload: MessageType = {
        "id": dic["messageId"], "content": dic["content"], "tts": False,
        "mention_everyone": False, "attachments": atch, "embeds":  dic["embeds"],
        "author": {
            "bot": user.bot, "id": user.id, "system": user.system,
            "username": user.name, "discriminator": user.discriminator,
            "avatar": user.display_avatar.url
        },
        "edited_timestamp": None, "type": 0, "pinned": False,
        "mentions": [], "mention_roles": [], "channel_id": self.share, #このbotが入ってないサーバーからだとバグりそうなのでjsonチャンネルをセット
        "timestamp": ""
        }
        channel = self.bot.get_channel(self.share)
        if not channel or not isinstance(channel, discord.abc.Messageable):
            raise ValueError("Unknown Channel Id.")
        message1 = discord.Message(
        data=payload, state=self.bot._get_state(), channel=channel
        )
        if channel.guild is not None:
            message1.author = channel.guild.get_member(user.id)  # type: ignore
            if message1.author == None:
                message1.author = user
        else:
            message1.author = user
        message1.id = dic["messageId"]
        dic.setdefault("reference", "")
        if dic["reference"] != "" and needref:
            reference_mid = dic["reference"]
            async for past_message in self.bot.get_channel(self.share).history(limit=1000):
                try:
                    past_dic = ujson.loads(past_message.content)
                except:
                    continue 
                if "type" in past_dic and past_dic["type"] != "message":
                    continue
                if not "messageId" in past_dic:
                    continue
                if str(past_dic["messageId"]) == str(reference_mid):
                    user = await self.bot.fetch_user(int(past_dic["userId"]))
                    atch = list()
                    c = 0
                    past_dic.setdefault("attachmentsUrl", list())
                    if past_dic["attachmentsUrl"] != []:
                        for fb in past_dic["attachmentsUrl"]:
                            atch.append(await self.filefromurl(fb,c))
                            c = c + 1
                    past_dic.setdefault("embeds", list())
                    payload: MessageType = {
                    "id": past_dic["messageId"], "content": past_dic["content"], "tts": False,
                    "mention_everyone": False, "attachments": atch, "embeds":  past_dic["embeds"],
                    "author": {
                        "bot": user.bot, "id": user.id, "system": user.system,
                        "username": user.name, "discriminator": user.discriminator,
                        "avatar": user.display_avatar.url
                    },
                    "edited_timestamp": None, "type": 0, "pinned": False,
                    "mentions": [], "mention_roles": [], "channel_id": self.share, #このbotが入ってないサーバーからだとバグりそうなのでjsonチャンネルをセット
                    "timestamp": ""
                    }
                    channel = self.bot.get_channel(self.share)
                    if not channel or not isinstance(channel, discord.abc.Messageable):
                        raise ValueError("Unknown Channel Id.")
                    message2 = discord.Message(
                    data=payload, state=self.bot._get_state(), channel=channel
                    )
                    if channel.guild is not None:
                        message2.author = channel.guild.get_member(user.id)  # type: ignore
                        if message2.author == None:
                            message2.author = user
                    else:
                        message2.author = user
                    message2.id = past_dic["messageId"]
                    message1.reference = CustmizedReference.from_message(message=message2)
                    message1.reference.cached_message1 = message2
        else:
            dic.pop("reference")
        return message1
    
    async def filefromurl(self, url: str, c: int):
        async with aiohttp.ClientSession() as session:  # セッションを作成
            async with session.get(url) as resp:  # URLからファイルを取得
                if resp.status != 200:
                    raise discord.HTTPException(resp, f'Failed to get asset from {url}')
                
                file_data = await resp.read()  # ファイルの内容を読み込む

                # URLからファイル名を抽出
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)

                with io.BytesIO(file_data) as file:
                    # ファイル名をURLから取得したものに設定
                    f = discord.File(file, filename)
                    fd = f.to_dict(index=c)
                    ap: AttachmentPayload = {
                        "id": fd["id"],
                        "size": sys.getsizeof(file),
                        "filename": fd["filename"],
                        "url": url,
                        'proxy_url': url
                    }
                    return ap

class CustmizedReference(discord.MessageReference):
    def __init__(self, *, message_id: int, channel_id: int, guild_id: Optional[int] = None, fail_if_not_exists: bool = True):
        self._state = None
        self.resolved = None
        self.message_id: Optional[int] = message_id
        self.channel_id: int = channel_id
        self.guild_id: Optional[int] = guild_id
        self.fail_if_not_exists: bool = fail_if_not_exists
        self.cached_message1 = None

async def setup(bot):
    await bot.add_cog(GlobalChat(bot))
