# RT - AutoMod

from typing import (
    Callable, Coroutine, Literal, Union, Optional, Any, DefaultDict, Tuple, Dict
)

from discord.ext import commands
import discord

from collections import defaultdict

from rtlib import RT

from .data_manager import GuildData, DataManager, require_cache
from .cache import Cache


def reply(description: str, color: str = "normal", **kwargs) -> dict:
    "埋め込み返信用のkwargsを作ります。"
    return {"title": "AutoMod", "description": description, "color": color, **kwargs}
OK = "Ok"


class AutoMod(commands.Cog, DataManager):

    COLORS = {
        "normal": 0x66b223,
        "warn": 0xDDBB04,
        "error": 0xF288AA
    }

    def __init__(self, bot: RT):
        self.bot = bot
        self.caches: DefaultDict[int, Tuple[GuildData, Dict[int, Cache]]] = \
            defaultdict(dict)
        super(commands.Cog, self).__init__(self)

    def cog_unload(self):
        self.close()

    Sendable = Union[commands.Context, discord.TextChannel]
    async def setting(
        self, function: Callable[..., Coroutine], channel: Sendable, *args, **kwargs
    ) -> discord.Message:
        "何かを設定するコマンドに便利な関数"
        args, kwargs = await function(channel, *args, **kwargs)
        return await self.reply(channel, *args, **kwargs)

    async def reply(self, channel: Sendable, *args, **kwargs) -> discord.Message:
        if kwargs:
            if "color" not in kwargs:
                kwargs["color"] = self.COLORS["normal"]
            elif isinstance(kwargs["color"], str):
                kwargs["color"] = self.COLORS[kwargs["color"]]
            kwargs = {"embed": discord.Embed(**kwargs)}
        return await channel.send(*args, **kwargs)

    @commands.group()
    @commands.has_permissions(administrator=True)
    @require_cache
    async def automod(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    async def nothing(self, _, *args, **kwargs):
        "settingで何もしたくない時のためのものです。"
        return args, kwargs

    async def toggle(
        self, channel: Sendable, mode: str, value: Union[bool, Any], *args, **kwargs
    ):
        "onoffするだけの設定を更新する関数です。"
        if value is False:
            del self.caches[channel.guild.id][0][mode]
        else:
            self.caches[channel.guild.id][0][mode] = value
        return args, kwargs

    @automod.group()
    async def warn(self, ctx: commands.Context):
        await self.automod(ctx)

    @warn.command()
    async def level(
        self, ctx: commands.Context, mode: Literal["ban", "mute"],
        toggle: bool, warn: float, *, role: Optional[discord.Role] = None
    ):
        if mode == "ban":
            await self.setting(self.toggle, ctx, "ban", not toggle or warn, OK)
        elif mode == "mute":
            if role:
                self.caches[ctx.guild.id][0]["mute"] = {
                    "role_id": role.id, "warn": warn
                }
                await self.setting(self.nothing, ctx, OK)
            else:
                await self.setting(self.toggle, ctx, "mute", False, OK)
        else:
            await self.reply(ctx, "ミュートにする場合はミュートの際につける役職を設定する必要があります。")

    @warn.command()
    @require_cache
    async def set(self, ctx: commands.Context, warn: float, *, member: discord.Member):
        ctx.member = member
        self.caches[ctx.guild.id][1][member.id].warn = warn
        await self.reply(ctx, OK)

    @warn.command()
    @require_cache
    async def check(self, ctx: commands.Context, *, member: discord.Member):
        ctx.member = member
        await self.reply(
            ctx, {
                "ja": f"{member.display_name}の現在の警告数：{self.caches[ctx.guild.id][1][member.id].warn}",
                "en": f"{member.display_name}'s current warn is {self.caches[ctx.guild.id][1][member.id].warn}."
            }
        )

    @warn.group()
    async def invites(self, ctx: commands.Context):
        await self.automod(ctx)

    @invites.group("ignore")
    async def invites_ignore(self, ctx: commands.Context):
        await self.automod(ctx)

    async def ignore_setting(
        self, channel: Sendable, mode: Literal["add", "remove", "toggle"],
        key: str, obj, *args, **kwargs
    ):
        "例外設定のコマンドでのsetting関数の使用ための"
        try:
            if mode == "add":
                if obj.id not in self.caches[channel.guild.id][0][key]:
                    self.caches[channel.guild.id][0][key].append(obj.id)
            elif mode == "remove":
                self.caches[channel.guild.id][0][key].remove(obj.id)
            else:
                if key in self.caches[channel.guild.id][0]:
                    del self.caches[channel.guild.id][0][key]
                else:
                    self.caches[channel.guild.id][0][key] = []
        except KeyError:
            return ("この機能は有効になっていません。",), kwargs
        except ValueError:
            return ("その例外は設定されていません。",), kwargs
        else:
            return args, kwargs

    @invites_ignore.command("add")
    async def add_invites_ignore(
        self, ctx: commands.Context,
        obj: Union[discord.Role, discord.TextChannel, discord.Object]
    ):
        await self.setting(self.ignore_setting, ctx, OK)


def setup(bot):
    bot.add_cog(AutoMod(bot))