# RT Dashboard - Setting

from __future__ import annotations

from typing import TypedDict, Union, Optional, Literal, overload

from asyncio import Event, sleep, wait_for, TimeoutError as AioTimeoutError
from datetime import datetime

from discord.ext import commands
import discord

from pytz import utc

from aiohttp import ClientSession
from ujson import dumps

from rtlib.rt_module.src.setting import CommandData
from rtlib import RT


def Setting(*args, **kwargs):
    "以前の設定デコレータの偽物"
    def decorator(func):
        return func
    return decorator


class CommandRunData(TypedDict, total=False):
    name: str
    kwargs: list[str]
    channel: int
    guild: int


class Context:
    "ダッシュボードから呼ばれたコマンドで実行されるContextです。"

    def __init__(
        self, cog: SettingManager, data: CommandRunData,
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
        self.replied = Event(loop=self.bot.loop)
        self.replied_content: Optional[str] = None

    async def trigger_typing(self):
        ...

    async def send(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        "返信をします。"
        self.replied_content = self.bot.cogs["Language"].get_text(
            embed if embed else content, self.author.id
        )
        if isinstance(content, discord.Embed):
            self.replied_content = content.to_dict()
        self.bot.print("[SettingManager]", "[Reply]", f"Content: {self.replied_content}")
        self.replied.set()

    @overload
    async def reply(
        self, content: str = None, embed: discord.Embed = None, *args, **kwargs
    ):
        ...

    async def delete(self) -> None:
        ...


class SettingManager(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot
        self.data: dict[str, CommandData] = {}

    @commands.Cog.listener()
    async def on_full_ready(self):
        await self.update()

    def session(self):
        "`aiohttp.ClientSession`の準備をする。"
        return ClientSession(loop=self.bot.loop, json_serialize=dumps)

    async def update(self):
        "コマンドのデータを用意してバックエンドにコマンドのデータを送信します。"
        # コマンドのデータを用意する。
        for command in self.bot.commands:
            if ("headding" in command.__original_kwargs__
                    or "headding" in command.extras):
                category = category = command.__original_kwargs__.get(
                    "category", command.extras.get("parent", "Other")
                )
                try:
                    h = self.bot.cogs["DocHelp"].data[category][
                        command.qualified_name[command.qualified_name.find(" "):]
                        if command.parent else command.name
                    ]
                except KeyError:
                    h = {"ja": "ヘルプが見つからなかった...", "en": "No help..."}
                self.data[command.qualified_name] = CommandData(
                    headding=command.__original_kwargs__.get("headding")
                        or command.extras.get("headding"),
                    category=category, help=h
                )
        # バックエンドにコマンドのデータを送信する。
        await self.bot.rtc.ready.wait()
        await self.bot.rtc.request("dashboard.update", self.data)

    async def run(self, data: CommandRunData) -> tuple[Literal["Error", "Ok"], str]:
        "コマンドを走らせます。"
        ctx = None
        try:
            # コマンドのメッセージを組み立てる。
            content = f"{self.bot.command_prefix[0]}{data['name']}"
            for parameter in self.commands[data["name"]].clean_params.values():
                tentative = f' "{data["kwargs"].get(parameter.name, "")}"'
                if parameter.kind == parameter.KEYWORD_ONLY:
                    tentative = f" {tentative[2:-1]}"
                content += tentative

            # 実行できるかチェックをしてからオリジナルContextでコマンドを実行する。
            ctx = Context(self, data, self.commands[data["name"]])
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

            await self.bot.invoke(ctx.message)
            try:
                await wait_for(ctx.replied.wait(), timeout=8)
            except AioTimeoutError:
                return ("Error", "Timeout")
            else:
                assert self.replied_content is not None
                return ("Ok", ctx.replied_content)
        except Exception as e:
            if ctx:
                self.bot.dispatch("command_error", ctx, e)
            return ("Error", str(e))


def setup(bot):
    bot.add_cog(SettingManager(bot))