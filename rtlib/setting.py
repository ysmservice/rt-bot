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
    channel_id: Union[int, Literal[0]]
    ip: str


class Setting:
    def __init__(
        self, mode: Literal["guild", "channel", "user"],
        name: Optional[str] = None
    ):
        self.mode, self.name = mode, name


class Context:
    "ダッシュボードから呼ばれたコマンドで実行されるContextです。"

    def __init__(
        self, cog: "SettingManager", data: CommandRunData, command: commands.Command
    ):
        self.data = data
        self.setting_manager = cog
        self.bot: "RT" = self.setting_manager.bot
        self.guild: Optional[discord.Guild] = self.bot.get_guild(data["guild_id"])
        self.channel: Optional[
            Union[discord.abc.GuildChannel, discord.DMChannel]
        ] = (
            self.guild.get_channel(data["channel_id"])
            if self.guild else self.bot.get_user(data["user_id"])
        )
        print(data["user_id"])
        self.author: Union[discord.User, discord.Member] = (
            self.guild.get_member(data["user_id"]) if self.guild
            else self.bot.get_user(data["user_id"])
        )
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
        async with self.setting_manager.session.post(
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

    def get_parsed_args(self, annotation: object) -> List[str]:
        "渡されたオブジェクトから設定項目の型の名前を判定し返します。"
        if isinstance(annotation, Option):
            annotation = annotation.annotation
        if annotation in (str, int, float, bool):
            return annotation.__name__
        elif getattr(annotation, "__name__", "") in (
            "Member", "User", "TextChannel", "VoiceChannel", "StageChannel",
            "Thread", "Role"
        ):
            return annotation.__name__.replace("Text", "").replace("Voice", "") \
                .replace("Stage", "").replace("Thread", "Channel").replace("User", "Member")
        elif (origin := get_origin(annotation)) == Union:
            return "str"
        elif origin == Literal:
            return list(get_args(annotation))
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
            data["guild" if setting.mode == "channel" else setting.mode] \
                [command.qualified_name] = {
                    "help": self.bot.cogs["BotGeneral"].get_command_url(command),
                    "kwargs": kwargs, "sub_category": getattr(
                        command.parent, "name", None
                    ), "headding": command.extras.get("headding"),
                    "require_channel": setting.mode == "channel",
                    "display_name": setting.name or command.name
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
            if await command.can_run(ctx := Context(self, data, command)):
                return await command(ctx, **data["kwargs"])
        except Exception as e:
            self.bot.dispatch("command_error", ctx, e)

    @commands.group("settest")
    async def setting_test(self, ctx: Context):
        ...

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
            }
        )
        content = {
            "content": f"# 返信テスト (content)\n{content}",
            "embed": discord.Embed(title="返信テスト (embed)", description=content)
        }
        del content["content" if embed else "embed"]
        await ctx.reply(**content)

    @setting_test.command(setting=Setting("channel"), aliases=["stc"])
    async def setting_test_channel(self, ctx: Context):
        await ctx.reply(f"You selected {ctx.channel.name}.")

    def cog_unload(self):
        if hasattr(self, "_session"):
            self.bot.loop.create_task(self._session.close())


def setup(bot):
    bot.add_cog(SettingManager(bot))