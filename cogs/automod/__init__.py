# RT - AutoMod

from typing import (
    Callable, Coroutine, Literal, Union, Any, DefaultDict, Dict, Tuple, List
)

from discord.ext import commands
import discord

from collections import defaultdict

from rtlib import RT

from .modutils import process_check_message, trial_new_member, trial_invite
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
        self.enabled: List[int] = []
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
        if ctx.invoked_subcommand:
            # もしまだAutoModを有効にしていない状態でこのコマンドのサブコマンドを実行したならエラーを起こす。
            assert ctx.guild.id in self.enabled
        else:
            await self.toggle_automod(ctx.guild.id)
            await ctx.reply(OK)

    @automod.error
    async def on_automod_error(
        self, ctx: commands.Context, exception: Union[AssertionError, Any]
    ):
        if isinstance(exception, AssertionError):
            await ctx.reply("このサーバーではAutoModが有効になっていません。\n`rt!automod`を実行してください。")
        else:
            raise exception

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
            self.caches[channel.guild.id][0][mode] = \
                self.DEFAULTS.get(mode) if value is True else value
        return args, kwargs

    @automod.group()
    async def warn(self, ctx: commands.Context):
        await self.automod(ctx)

    @warn.command()
    async def level(
        self, ctx: commands.Context, mode: Literal["ban", "mute"],
        warn: Union[bool, float]
    ):
        await self.setting(self.toggle, ctx, mode, warn, OK)

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

    @warn.group()
    async def invites(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await self.setting(
                self.ignore_setting, ctx, "toggle", "invites", None, OK
            )

    @invites.command("ignore")
    async def invites_ignore(
        self, ctx: commands.Context, mode: Literal["add", "remove"],
        obj: Union[discord.Role, discord.TextChannel, discord.Object]
    ):
        await self.setting(self.ignore_setting, ctx, mode, "invites", obj, OK)

    @warn.group()
    async def deleter(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await self.setting(
                self.ignore_setting, ctx, "toggle", "invite_deleter", None, OK
            )

    @deleter.group("ignore")
    async def deleter_ignore(
        self, ctx: commands.Context, mode: Literal["add", "remove"],
        obj: Union[discord.Role, discord.TextChannel, discord.Object]
    ):
        await self.setting(
            self.ignore_setting, ctx, mode, "invite_deleter", obj, OK
        )

    @warn.command()
    async def bolt(self, ctx: commands.Context, seconds: Union[bool, float]):
        await self.setting(self.toggle, ctx, "bolt", seconds, OK)

    @warn.command()
    async def emoji(self, ctx: commands.Context, count: Union[bool, int]):
        await self.setting(self.toggle, ctx, "emoji", count, OK)

    async def prepare_cache(self, guild: discord.Guild, member: discord.Member):
        await self.prepare_cache_guild(guild)
        await self.prepare_cache_member(member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild and message.guild.id in self.enabled:
            await self.prepare_cache(message.guild, message.author)
            process_check_message(
                self.caches[message.guild.id][1][message.author.id],
                self.caches[message.guild.id][0], message
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id in self.enabled:
            await self.prepare_cache(member.guild, member)
            await trial_new_member(
                self.caches[member.guild.id][1][member.id],
                self.caches[member.guild.id][0]
            )

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild.id in self.enabled:
            await self.prepare_cache_guild(invite.guild)
            await trial_invite(self.caches[invite.guild.id][0], invite)


def setup(bot):
    bot.add_cog(AutoMod(bot))