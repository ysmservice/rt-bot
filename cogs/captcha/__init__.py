# RT - Captcha

from typing import TypedDict, Literal, Union, Optional, Any, Tuple, DefaultDict, Dict

from discord.ext import commands, tasks
import discord

from rtutil import DatabaseManager
from rtlib import RT

from aiohttp import ClientSession
from aiomysql import Cursor

from collections import defaultdict
from dataclasses import dataclass
from ujson import loads, dumps
from time import time

from .image import ImageCaptcha, QueueData as ImageQueue
from .web import WebCaptcha
from .word import WordCaptcha
from .click import ClickCaptcha


Mode = Literal["image", "web", "word"]


@dataclass
class Captchas:
    image: ImageCaptcha
    word: WordCaptcha
    web: WebCaptcha
    click: ClickCaptcha


class Timeout(TypedDict):
    kick: bool
    time: float


class WordData(TypedDict):
    word: str
    channel_id: int


class Extras(TypedDict, total=False):
    timeout: Timeout
    data: Union[WordData, Any]


@dataclass
class QueueData:
    mode: Mode
    role_id: int
    extras: Extras


class DataManager(DatabaseManager):
    "セーブデータを管理するためのクラスです。"

    TABLES = ("captchaData",)

    def __init__(self, cog: "Captcha"):
        self.cog, self.pool = cog, cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self, cursor: Cursor = None):
        await cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {self.TABLES[0]} (
                GuildID BIGINT PRIMARY KEY NOT NULL,
                Mode TEXT, RoleID BIGINT, Extras JSON
            );"""
        )

    async def write(
        self, guild_id: int, mode: Mode, role_id: int,
        extras: Extras, cursor: Cursor = None
    ) -> None:
        "認証設定を保存します。"
        await cursor.execute(
            f"""INSERT INTO {self.TABLES[0]} VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE Mode = %s, RoleID = %s, Extras = %s;""",
            (
                guild_id, mode, role_id, (extras := dumps(extras)),
                mode, role_id, extras
            )
        )

    async def read(
        self, guild_id: int, cursor: Cursor = None
    ) -> Optional[Tuple[Mode, int, Extras]]:
        "認証設定を読み込みます。"
        await cursor.execute(
            f"""SELECT Mode, RoleID, Extras FROM {self.TABLES[0]}
                WHERE GuildID = %s;""",
            (guild_id,)
        )
        if (row := await cursor.fetchone()):
            return list(row[:-1]) + [loads(row[-1])]

    async def timeout(
        self, guild_id: int, time_: float, kick: bool, cursor: Cursor = None
    ) -> None:
        "認証設定にタイムアウトを設定します。"
        assert (row := await self.read(guild_id, cursor=cursor)), "設定がありません。"
        data = row[-1]
        data["timeout"] = {"time": time_, "kick": kick}
        await cursor.execute(
            f"UPDATE {self.TABLES[0]} SET Extras = %s;",
            (dumps(data),)
        )


class View(discord.ui.View):
    "認証開始ボタンのViewです。"

    def __init__(self, cog: "Captcha", emoji: Optional[str] = None, *args, **kwargs):
        self.cog = cog
        super().__init__(*args, **kwargs)
        if emoji is not None:
            self.children[0].emoji = emoji

    @discord.ui.button(label="Start Captcha", custom_id="captcha", emoji="🔎")
    async def start_captcha(self, _, interaction: discord.Interaction):
        if self.cog.queued(interaction.guild_id, interaction.user.id):
            if (row := await self.cog.read(interaction.guild_id)):
                # もし認証の設定がされているサーバーなら認証を開始する。
                if hasattr(captcha := self.cog.get_captcha(row[0]), "on_captcha"):
                    await captcha.on_captcha(interaction)
                else:
                    await interaction.response.send_message(
                        "このサーバーで設定されている認証の種類がこのボタンを押す方式とあっていません。",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "このサーバーで認証の設定がされていないので認証を開始することができません。",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "あなたは認証対象ではありません。", ephemeral=True
            )


QueueDataT = Union[QueueData, ImageQueue]


class Captcha(commands.Cog, DataManager):

    BASE = "/api/captcha/"

    def __init__(self, bot: RT):
        self.bot = bot
        self.queue: DefaultDict[
            int, Dict[int, Tuple[float, bool, QueueDataT]]
        ] = defaultdict(dict)
        self.queue_remover.start()
        self.view = View(self, timeout=None)
        self.bot.add_view(self.view)
        self.captchas = Captchas(
            ImageCaptcha(self), WordCaptcha(self),
            WebCaptcha(self), ClickCaptcha(self)
        )
        super(commands.Cog, self).__init__(self)

    def session(self):
        "`aiohttp.ClientSession`を手に入れるためのものです。"
        return ClientSession(loop=self.bot.loop, json_serialize=dumps)

    def print(self, *args, **kwargs) -> None:
        return self.bot.print("[Captcha]", *args, **kwargs)

    @commands.group(aliases=["auth", "cta", "認証"])
    async def captcha(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.reply(
                {"ja": "使用方法が違います。", "en": "It is wrong way to use this command."}
            )

    async def send_panel(
        self, channel: Union[discord.TextChannel, commands.Context], **kwargs
    ) -> discord.Message:
        "認証ボタンのパネルを送信するための関数です。"
        return await channel.send(
            embed=discord.Embed(
                **kwargs, color=self.bot.Colors.normal
            ), view=self.view
        )

    BELLOW = {
        "ja": "以下のボタンを押すことで認証を開始することができます。",
        "en": "Press the button bellow to start image captcha."
    }

    @captcha.command(aliases=["画像", "img"])
    async def image(self, ctx: commands.Context, *, role: discord.Role):
        await self.send_panel(
            ctx, title={
                "ja": "画像認証", "en": "Image Captcha"
            }, description=self.BELLOW
        )
        await self.write(ctx.guild.id, "image", role.id, {})
        await ctx.reply("Ok")

    @captcha.command(aliases=["合言葉", "wd"])
    async def word(self, ctx: commands.Context, word: str, *, role: discord.Role):
        await self.write(
            ctx.guild.id, "word", role.id, {
                "data": {"word": word, "channel_id": ctx.channel.id}
            }
        )
        await ctx.reply("Ok")

    @captcha.command(aliases=["ウェブ", "wb"])
    async def web(self, ctx: commands.Context, *, role: discord.Role):
        await self.send_panel(
            ctx, title={
                "ja": "ウェブ認証", "en": "Web Captcha"
            }, description=self.BELLOW
        )
        await self.write(ctx.guild.id, "web", role.id, {})
        await ctx.reply("Ok")

    @captcha.command(aliases=["ボタン", "クリック", "c"])
    async def click(self, ctx: commands.Context, *, role: discord.Role):
        await self.send_panel(
            ctx, title={
                "ja": "ワンクリック認証", "en": "One Click Captcha"
            }, description={
                "ja": "役職を手に入れるには以下のボタンを押してください。",
                "en": "To get the roll, press the button below."
            }
        )
        await self.write(ctx.guild.id, "click", role.id, {})
        await ctx.reply("Ok")

    @captcha.command("timeout", aliases=["タイムアウト", "t"])
    async def timeout_(self, ctx: commands.Context, timeout: float, kick: bool):
        if 0 <= timeout <= 1080:
            try:
                await self.timeout(ctx.guild.id, timeout, kick)
            except AssertionError:
                await ctx.reply(
                    {"ja": "このサーバーは認証の設定がされていないので、タイムアウトを設定することができません。",
                     "en": "I couldn't set a timeout because it was not set the captcha setting yet."}
                )
            else:
                await ctx.reply("Ok")
        else:
            await ctx.reply(
                {"ja": "タイムアウトは一分から三時間の範囲内である必要があります。",
                 "en": "Timeout must be set from one minute to three hours."}
            )

    def get_captchas(self) -> map:
        return map(lambda x: getattr(self.captchas, x), self.captchas)

    async def dispatch(self, captcha: object, name: str, *args, **kwargs) -> Optional[Any]:
        # 各Captchaクラスにある関数をあれば実行します。
        if hasattr(captcha, name):
            return await getattr(captcha, name)(*args, **kwargs)

    def queued(self, guild_id: int, member_id: int) -> bool:
        # 渡されたIDがqueueとしてキャッシュされているかを確認します。
        return guild_id in self.queue and member_id in self.queue[guild_id]

    async def remove_queue(
        self, guild_id: int, member_id: int, data: Optional[QueueDataT] = None
    ) -> None:
        "Queueを削除します。"
        if data is None:
            data = self.queue[guild_id][member_id][2]
        for captcha in self.get_captchas:
            await self.dispatch(captcha, "on_queue_remove", guild_id, member_id, data)
        del self.queue[guild_id][member_id]

    def cog_unload(self):
        self.queue_remover.cancel()

    @tasks.loop(seconds=10)
    async def queue_remover(self):
        # タイムアウトしたキューを消すためのループです。
        now = time()
        for guild_id, members in list(self.queue.items()):
            for member_id, (time_, kick, data) in list(members.items()):
                if now >= time_:
                    # タイムアウトしたキューを消す。
                    del self.members[member_id]
                    # もしキック設定がされている場合はキックを行う。
                    if kick and (guild := self.bot.get_guild(guild_id)):
                        await guild.kick(
                            discord.Object(member_id), reason="[Captcha] Timeout"
                        )
                    # キューの削除を行う。
                    self.bot.loop.create_task(self.remove_queue(guild_id, member_id, data))

    def get_captcha(self, mode: Mode) -> Union[ImageCaptcha, None]:
        return getattr(self.captchas, mode)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if (member.id not in self.queue.get(member.guild.id, {})
                and (row := await self.read(member.gulid.id))):
            # もし認証が設定されているサーバーの場合はqueueにタイムアウト情報を追加しておく。
            self.queue[member.guild.id][member.guild.id] = (
                time() + row[2].get("timeout", {}).get("time", 360),
                row[2].get("timeout", {}).get("kick", False),
                QueueData(row[0], row[1], row[2])
            )
            # もしCpatchaクラスにon_member_joinがあるならQueueDataに値を設定できるようにそれを呼び出す。
            await self.dispatch(self.get_captcha(row[0]), "on_member_join", member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 合言葉認証に必要なのでon_messageを呼び出しておく。
        if self.queued(message.guild.id, message.author.id):
            for captcha in self.captchas:
                await self.dispatch(captcha, "on_message", message)


def setup(bot):
    bot.add_cog(Captcha(bot))