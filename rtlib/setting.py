# RT Lib - Setting

from typing import (
    TYPE_CHECKING, TypedDict, Optional, Union, Literal, Dict, Tuple, List,
    overload, get_origin, get_args
)

from discord.ext import commands
import discord

from collections import defaultdict
from aiohttp import ClientSession
from inspect import signature
from ujson import dumps

from .websocket import websocket
from .slash import Option

if TYPE_CHECKING:
    from .typed import RT


class CommandRunData(TypedDict):
    command: str
    kwargs: Dict[str, str]
    guild_id: Union[int, Literal[0]]
    user_id: int
    channel_id: Union[int, Literal[0]]
    ip: str


class Context:
    "ダッシュボードから呼ばれたコマンドで実行されるContextです。"

    def __init__(self, bot: RT, data: CommandRunData, command: commands.Command):
        self.data = data
        self.bot = bot
        self.guild: Optional[discord.Guild] = self.bot.get_guild(data["guild_id"])
        self.channel: Optional[
            Union[discord.abc.GuildChannel, discord.DMChannel]
        ] = (
            self.guild.get_channel(data["channel_id"])
            or self.bot.get_user(data["user_id"])
        )
        self.author: Union[discord.User, discord.Member] = (
            self.guild.get_member(data["user_id"]) if self.guild
            else self.bot.get_user(data["user_id"])
        )
        self.command = command
        self.cog = command.cog
        self.voice_client: Optional[discord.VoiceClient] = \
            getattr(self.guild, "voice_client", None)
        self.prefix = "r2!" if bot.test else "rt!"
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
        async with self.bot.session.post(
            f"{self.bot.get_url()}/api/settings/reply/{self.data['ip']}",
            data=self.bot.cogs["Language"].get_text(
                embed.to_dict() if embed else content, self.author.id
            )
        ) as r:
            if self.bot.test:
                self.bot.print("[SettingManager]", "[POST]", await r.text())

    @overload
    async def reply(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        ...


class SettingManager(commands.Cog):
    def __init__(self, bot: "RT"):
        self.bot = bot
        self.data: Dict[
            str, Tuple[
                commands.Command, Literal["user", "guild", "channel"]
            ]
        ] = {}

    async def session(self) -> ClientSession:
        if not hasattr(self, "session"):
            self._session = ClientSession(
                loop=self.bot.loop, json_serialize=dumps,
                raise_for_errors=True
            )
        return self._session

    def get_parsed_args(self, annotation: object) -> List[str]:
        "渡されたオブジェクトから設定項目の型の名前を判定し返します。"
        if isinstance(annotation, Option):
            annotation = annotation.annotation
        if annotation in (str, int, float, bool):
            return [annotation.__name__]
        elif getattr(annotation, "__name__", "") in (
            "Member", "User", "TextChannel", "VoiceChannel", "StageChannel", "Thread",
            "Role", "Message", "Guild"
        ):
            return [annotation.__name__]
        elif isinstance(origin := get_origin(annotation), Union):
            return ["Literal"] + [
                self.get_parsed_args(child) for child in get_args(annotation)
            ]
        elif isinstance(origin, Literal):
            return ["str"] * len(get_args(annotation))
        else:
            return ["str"]

    @commands.Cog.listener()
    async def on_command_add(self, command: commands.Command):
        if command.__original_kwargs__.get("setting"):
            self.data[command.qualified_name] = (
                command, command.__original_kwargs__["setting"]
            )

    @commands.Cog.listener()
    async def on_update_api(self):
        "APIにBotにあるコマンドの設定のJSONデータを送る。"
        # データを作る。
        data = defaultdict(dict)
        for command, (category, mode) in self.data.values():
            kwargs = {
                parameter.name: self.get_parsed_args(parameter.annotation)
                for parameter in signature(command._callback).parameters.values()
            }
            data[category][command.name] = {
                "help": self.bot.cogs["Help"].get_command_url(command),
                "kwargs": kwargs, "mode": mode, "sub_category": getattr(
                    command.parent, "name", None
                ), "headding": command.extras.get("headding")
            }
        # データを送る。
        async with self.bot.session.post(
            f"{self.bot.get_url()}/api/settings/commands/update",
            json=data
        ) as r:
            if self.bot.test:
                self.bot.print("[SettingManager]", "Posted command setting data.")

    @websocket.websocket("/api/settings/websocket")
    async def setting_websocket(self, ws: websocket.WebSocket, _):
        # ユーザーがダッシュボードから設定を更新した際に、すぐに反応できるようにするためのものです。
        await ws.send("on_ready")

    @setting_websocket.event("on_post")
    async def post(self, ws: websocket.WebSocket, data: CommandRunData):
        self.bot.loop.create_task(
            self.run_command(self.data[data["command"]][0], data),
            name=f"UpdateSetting[{data['command']}]: {data['user_id']}"
        )
        await ws.send("on_posted")

    @setting_websocket.event("on_posted")
    async def posted(self, ws: websocket.WebSocket, _):
        await self.setting_websocket(ws)

    async def run_command(self, command: commands.Command, data: CommandRunData):
        "コマンドを走らせます。"
        try:
            if await command.can_run(ctx := Context(self.bot, data, command)):
                return await command(ctx, **data["kwargs"])
        except Exception as e:
            self.bot.dispatch("command_error", ctx, e)


def setup(bot):
    bot.add_cog(SettingManager(bot))