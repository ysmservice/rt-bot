# RT Lib - Setting

from typing import (
    TYPE_CHECKING, TypedDict, Optional, Union, Literal, Dict, Tuple, List,
    overload, get_origin, get_args
)

from discord.ext import commands
import discord

from collections import defaultdict
from aiohttp import ClientSession
from functools import partial
from datetime import datetime
from ujson import dumps
from time import time
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
    @overload
    def __init__(
        _, mode: str, name: Optional[str] = None,
        help_command: Tuple[str, str] = None, **kwargs
    ):
        ...

    def __new__(cls, mode, name=None, help_command=None, **kwargs):
        return lambda func: func
        self = super().__new__(cls)
        self.mode, self.name, self.kwargs = mode, name, kwargs
        self.help_command = help_command
        def _decorator(func):
            func._setting = self
            return func
        return _decorator


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
            self.bot.print(
                "[SettingManager]", "[Reply]",
                f"Response: {await r.text()}, Content: {content}"
            )

    @overload
    async def reply(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        ...

    async def delete(self) -> None:
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
                loop=self.bot.loop, json_serialize=partial(
                    dumps, ensure_ascii=False
                )
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

    def reset(self):
        self.data = {}

    def add_command(self, command: commands.Command) -> None:
        self.data[command.qualified_name] = (command, command.callback._setting)

    @commands.Cog.listener()
    async def on_command_add(self, command: commands.Command):
        if hasattr(command.callback, "_setting"):
            self.add_command(command)

    @commands.Cog.listener("on_update_api")
    async def update(self):
        "APIにBotにあるコマンドの設定のJSONデータを送る。"
        # バックエンド用のデータを作る。
        data = defaultdict(dict)
        for command, setting in self.data.values():
            kwargs = {
                parameter.name: (
                    ant := self.get_parsed_args(parameter.annotation),
                    "" if parameter.default == parameter.empty
                    else parameter.default,
                    parameter.kind == parameter.KEYWORD_ONLY \
                        and ant == "str"
                ) for parameter in command.clean_params.values()
            }
            kwargs.update({
                key: (self.get_parsed_args(value), "", False)
                for key, value in setting.kwargs.items()
            })
            data[setting.mode][command.qualified_name] = {
                "help": (
                    self.bot.cogs["BotGeneral"].get_help_url(*setting.help_command)
                    if setting.help_command
                    else self.bot.cogs["BotGeneral"].get_command_url(command)
                ), "kwargs": kwargs, "sub_category": getattr(
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
            self.bot.print("[SettingManager]", "[Updater]", time(), await r.text())
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
        ctx = None
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
            if ctx:
                self.bot.dispatch("command_error", ctx, e)

    def cog_unload(self):
        if hasattr(self, "_session"):
            self.bot.loop.create_task(self._session.close())


def setup(bot):
    return
    bot.add_cog(SettingManager(bot))
