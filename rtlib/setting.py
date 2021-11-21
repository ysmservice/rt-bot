# RT Lib - Setting

from typing import (
    TYPE_CHECKING, TypedDict, Optional, Union, Literal, Dict, Tuple, List,
    overload, get_origin, get_args
)

from discord.ext import commands
import discord

from collections import defaultdict
from aiohttp import ClientSession
from traceback import print_exc
from inspect import signature
from datetime import datetime
from asyncio import sleep
from ujson import dumps
from pytz import utc

from . import websocket
from .slash import Option

if TYPE_CHECKING:
    from .typed import RT


class CommandRunData(TypedDict):
    command: str
    kwargs: Dict[str, Union[str, int, float, bool]]
    guild_id: Union[int, Literal[0]]
    category: str
    user_id: int
    ip: str


class Setting:
    def __init__(
        self, mode: Literal["guild", "channel", "user"],
        name: Optional[str] = None, **kwargs
    ):
        self.mode, self.name, self.kwargs = mode, name, kwargs


class Context:
    "ダッシュボードから呼ばれたコマンドで実行されるContextです。"

    def __init__(
        self, cog: "SettingManager", data: CommandRunData,
        command: commands.Command, **kwargs
    ):
        # IDを文字列から整数に変換する。
        for key, value in list(data.items()):
            if key.endswith("id"):
                data[key] = int(value)

        # 変数を作っていく。
        self.data = data
        self.setting_manager = cog
        self.bot: "RT" = self.setting_manager.bot
        self.guild: Optional[discord.Guild] = self.bot.get_guild(data["guild_id"])
        self.created_at: datetime = datetime.now(utc)
        self.edited_at = None
        self.__setting_context__ = True

        self.channel: Optional[
            Union[discord.abc.GuildChannel, discord.DMChannel]
        ] = (
            self.guild.get_channel(data["kwargs"].pop(
                "channel_id", data["kwargs"].pop(
                    "channel", data["kwargs"].pop("Channel", 0)
                )
            ))
            if data["category"].endswith("guild")
            else self.bot.get_user(data["user_id"])
        )
        self.author: Union[discord.User, discord.Member] = (
            self.guild.get_member(data["user_id"]) if self.guild
            else self.bot.get_user(data["user_id"])
        )
        for key in kwargs:
            setattr(self, key, kwargs.pop(key, None))
        self.command = command
        self.cog = command.cog
        self.voice_client: Optional[discord.VoiceClient] = \
            getattr(self.guild, "voice_client", None)
        self.prefix = "r2!" if self.bot.test else "rt!"
        self.me: Union[discord.Member, discord.ClientUser] = \
            getattr(self.guild, "me", self.bot.user)
        self.message = self
        self.reply = self.send

    async def trigger_typing(self):
        ...

    async def send(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        "返信をします。"
        content = self.bot.cogs["Language"].get_text(
            embed if embed else content, self.author.id
        )
        if isinstance(content, discord.Embed):
            content = content.to_dict()
        async with self.setting_manager.session.post(
            f"{self.bot.get_url()}/api/settings/reply/{self.data['ip']}",
            json={"data": content}
        ) as r:
            if self.bot.test:
                self.bot.print("[SettingManager]", "[POST]", await r.text())

    @overload
    async def reply(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        ...


class SettingManager(commands.Cog):

    SUPPORTED_DISCORD_ANNOTATIONS = (
        "Member", "User", "TextChannel", "VoiceChannel", "StageChannel",
        "Thread", "Role"
    )
    SUPPORTED_ANNOTATIONS = (str, int, float, bool)

    def __init__(self, bot: "RT"):
        self.bot = bot
        self.data: Dict[
            str, Tuple[commands.Command, Setting]
        ] = {}
        self.before = {}

    @property
    def session(self) -> ClientSession:
        if not hasattr(self, "_session"):
            self._session = ClientSession(
                loop=self.bot.loop, json_serialize=dumps
            )
        return self._session

    def get_parsed_args(self, annotation: object) -> Union[str, List[str]]:
        "渡されたオブジェクトから設定項目の型の名前を判定し返します。"
        if isinstance(annotation, Option):
            annotation = annotation.annotation
        if annotation in self.SUPPORTED_ANNOTATIONS:
            return annotation.__name__
        elif getattr(annotation, "__name__", "") in self.SUPPORTED_DISCORD_ANNOTATIONS:
            return annotation.__name__.replace("Text", "").replace("Voice", "") \
                .replace("Stage", "").replace("Thread", "Channel").replace("User", "Member")
        elif (origin := get_origin(annotation)) == Union:
            return ["Union"] + [self.get_parsed_args(arg) for arg in get_args(annotation)]
        elif origin == Literal:
            return ["Literal"] + list(get_args(annotation))
        else:
            return "str"

    @commands.Cog.listener()
    async def on_command_add(self, command: commands.Command):
        if command.__original_kwargs__.get("setting"):
            self.data[command.qualified_name] = (
                command, command.__original_kwargs__["setting"]
            )

    @commands.Cog.listener("on_update_api")
    async def update(self):
        "APIにBotにあるコマンドの設定のJSONデータを送る。"
        # データを作る。
        data = defaultdict(dict)
        for command, setting in self.data.values():
            kwargs = {
                parameter.name: (
                    self.get_parsed_args(parameter.annotation),
                    "" if parameter.default == parameter.empty
                    else parameter.default, parameter.kind == parameter.KEYWORD_ONLY
                ) for parameter in signature(command._callback).parameters.values()
                if parameter.name not in ("self", "ctx")
            }
            kwargs.update({
                key: (self.get_parsed_args(value), "", False)
                for key, value in setting.kwargs.items()
            })
            data[setting.mode][command.qualified_name] = {
                "help": self.bot.cogs["BotGeneral"].get_command_url(command),
                "kwargs": kwargs, "sub_category": getattr(
                    command.parent, "name", None
                ), "headding": (
                    command.extras.get("headding")
                    or command.__original_kwargs__.get("headding")
                ), "display_name": setting.name or command.name
            }
        # データを送る。
        async with self.bot.session.post(
            f"{self.bot.get_url()}/api/settings/commands/update",
            json=data
        ) as r:
            if self.bot.test:
                ...
                # self.bot.print("[SettingUpdater]", await r.text())
        self.before = data

    @websocket.websocket("/api/settings/websocket", auto_connect=True, reconnect=True)
    async def setting_websocket(self, ws: websocket.WebSocket, _):
        # ユーザーがダッシュボードから設定を更新した際に、すぐに反応できるようにするためのものです。
        await ws.send("on_ready")

    @setting_websocket.event("on_post")
    async def post(self, ws: websocket.WebSocket, data: CommandRunData):
        if isinstance(data, dict):
            self.bot.loop.create_task(
                self.run_command(self.data[data["command"]][0], data),
                name=f"UpdateSetting[{data.get('command')}]: {data.get('user_id')}"
            )
        await ws.send("on_posted")

    @setting_websocket.event("on_posted")
    async def posted(self, ws: websocket.WebSocket, _):
        await self.setting_websocket(ws, None)

    async def run_command(self, command: commands.Command, data: CommandRunData):
        "コマンドを走らせます。"
        try:
            # コマンドのメッセージを組み立てる。
            content = f"{self.bot.command_prefix[0]}{command.qualified_name}"
            for parameter in command.clean_params.values():
                tentative = f' "{data["kwargs"].get(parameter.name, "")}"'
                if parameter.kind == parameter.KEYWORD_ONLY:
                    tentative = f" {tentative[2:-1]}"
                content += tentative

            # 実行できるかチェックをしてからオリジナルContextでコマンドを実行する。
            ctx = Context(self, data, command)
            ctx.content = content
            ctx._state = self.bot.http
            parsed_ctx = await self.bot.get_context(ctx)
            ctx.view = parsed_ctx.view
            ctx.args, ctx.kwargs = parsed_ctx.args, parsed_ctx.kwargs
            for name in dir(parsed_ctx):
                if not name.startswith(
                    (
                        "__", "send", "reply", "trigger", "typing", "created",
                        "channel", "message", "guild"
                    )
                ):
                    setattr(ctx, name, getattr(parsed_ctx, name))

            return await self.bot.invoke(ctx.message)
        except Exception as e:
            self.bot.dispatch("command_error", ctx, e)

    @commands.group("settest")
    async def setting_test(self, ctx: Context):
        ...

    """
    @setting_test.command(
        extras={
            "headding": {
                "ja": "ダッシュボードテスト用のコマンド",
                "en": "Test command for dashboard"
            }, "parent": "Other"
        }, setting=Setting("guild", "Setting Test Command")
    )
    async def setting_test_guild(
        self, ctx: Context, normal, number: int, member: discord.Member,
        channel: discord.TextChannel, member_or_str: Union[discord.Member, str],
        literal: Literal["1", "2", "3"], embed: bool, default="aiueo",
        *, bigbox
    ):
        content = "\n".join(
            f"* {key}: {value}" for key, value in {
                "normal": normal, "number": number, "member": member,
                "channel": channel, "member_or_str": member_or_str,
                "literal": literal, "embed": embed, "default": default,
                "bigbox": bigbox.replace("\n", " [改行] ")
            }.items()
        )
        content = {
            "content": f"# 返信テスト (content)\n{content}",
            "embed": discord.Embed(title="返信テスト (embed)", description=content)
        }
        del content["content" if embed else "embed"]
        await ctx.reply(**content)
    """

    @setting_test.command(
        setting=Setting("guild", channel=discord.TextChannel),
        aliases=["stc"], headding={
            "ja": "メッセージを特定のチャンネルに送信します。", "en": "Send message"
        }, parent="ServerTool"
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def send(self, ctx: Context, *, content: str):
        await ctx.channel.send(content)
        await ctx.reply(f"{ctx.channel.name}にメッセージを送信しました。")

    @commands.command(
        setting=Setting("user"), headding={
            "ja": "IDチェッカー", "en": "ID Checker"
        }, parent="Individual"
    )
    async def checker(self, ctx):
        await ctx.reply(f"あなたのIDは`{ctx.author.id}`です。")

    @commands.command(setting=Setting("Tools", "Loading表示"))
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def setting_test_loading(self, ctx: Context, number: Literal[1, 2, 3, 4, 5]):
        await sleep(number)
        await ctx.reply("Loading楽しかった？")

    OKES = ["+", "-", "*", "/", "."]
    OKCHARS = list(map(str, range(9))) + OKES

    def safety(self, word):
        return "".join(char for char in str(word) if char in self.OKCHARS)

    @commands.command(
        setting=Setting("Tools", "簡易電卓"), headding={
            "ja": "式を入力して計算を行うことができます。", "en": "Calculation by expression"
        }, parent="Individual"
    )
    async def calc(
        self, ctx: Context, *, expression: str
    ):
        if len(expression) < 400:
            await ctx.reply(f"計算結果：`{eval(self.safety(expression))}`")
        else:
            raise commands.BadArgument("計算範囲が大きすぎます！頭壊れます。")

    @commands.command(
        setting=Setting("Tools", "文字列逆順"),
        headding={
            "ja": "文字列を逆順にします。", "en": "Reverse text"
        },
        parent="Individual"
    )
    async def reverse(self, ctx: Context, *, bigbox):
        await ctx.reply(f"結果：\n```\n{bigbox[::-1]}\n```")

    @commands.command(
        setting=Setting("Tools", "文字列交換"),
        headding={
            "ja": "文字列の交換を行います。", "en": "Replace text"
        }, parent="Individual"
    )
    async def replace(self, ctx: Context, before, after, *, text):
        await ctx.reply(f"結果：{text.replace(before, after)}")

    def cog_unload(self):
        if hasattr(self, "_session"):
            self.bot.loop.create_task(self._session.close())


def setup(bot):
    bot.add_cog(SettingManager(bot))
