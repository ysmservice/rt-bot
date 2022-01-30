# RT - rocations

from __future__ import annotations

from typing import TypeVar, TypedDict, Optional

from collections import OrderedDict
from functools import wraps
from time import time

from discord.ext import commands, tasks

from rtlib import RT, Table, Context


# データ型等
class Nice(TypedDict):
    user_id: int
    user_name: str
    message: Optional[str]


class Server(TypedDict):
    description: str
    tags: list[str]
    invite: str
    nices: list[Nice]
    raised: float


class RocationsData(Table):
    __allocation__ = "Guild"
RocationsData.__annotations__ = Server.__annotations__
RAISE_TIME = 14106 # 3時間55分06秒
Servers = OrderedDict[int, Server]
SIZE_PER_INDEX = 10


# 何か必要なもの
CheckFT = TypeVar("CheckFT")
def check(function: CheckFT) -> CheckFT:
    "宣伝が有効になっているか"
    @wraps(function)
    async def new(self: Rocations, ctx: Context, *args, **kwargs):
        if ctx.guild.id in self.data:
            return await function(self, ctx, *args, **kwargs)
        else:
            return await ctx.reply(
                "このサーバーではRocationsにサーバーが登録されていません。"
                "\n`rt!rocations toggle`で登録してください。"
            )
    return new


# ほんへ
class Rocations(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot
        self.data = Server(bot)
        self._sorted_cache: list[Servers] = {}

        self.bot.rtc.set_event(self.get_rocations)
        self._process_cache.start()

    @tasks.loop(seconds=10)
    async def _process_cache(self):
        # キャッシュを処理します。
            # 十個ずつRaisedされた順でサーバー一覧のキャッシュを作っていく。
        i, now = 0, OrderedDict()
        for guild_id, data in sorted(
            list(self.data.to_dict().items()), key=lambda x: x[0].get("raised", 0.0)
        ):
            i += 1
            now[guild_id] = data
            if i == SIZE_PER_INDEX:
                self._sorted_cache.insert(0, now)
                now, i = OrderedDict(), 0
        if i != SIZE_PER_INDEX:
            self._sorted_cache.insert(0, now)
            now = OrderedDict()

    def cog_unload(self):
        self._process_cache.cancel()

    def get_rocation(self, guild_id: int) -> Optional[Server]:
        "指定されたサーバーIDのRocationを取得します。"
        if guild_id in self.data:
            return self.data[guild_id].to_dict()

    def get_rocations(self, page: int) -> Optional[Servers]:
        "指定されたページのRocationsを取得します。"
        try:
            return self._sorted_cache[page]
        except KeyError:
            ...

    @commands.group()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def rocations(self, ctx: Context):
        if ctx.invoked_subcommand:
            await ctx.reply("Ok")
        else:
            await ctx.reply("使用方法が違います。")

    @rocations.command()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def toggle(self, ctx: Context):
        if ctx.guild.id in self.data:
            del self.data[ctx.guild.id]
        else:
            self.data[ctx.guild.id]

    @rocations.command()
    @check
    async def tags(self, ctx: Context, *, tags: str):
        self.data[ctx.guild.id].tags = tags.split("/")

    @rocations.command()
    @check
    async def description(self, ctx: Context, *, description: str):
        self.data[ctx.guild.id].description = description

    @rocations.command()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def invite(self, ctx: Context):
        self.data[ctx.guild.id].invite = (
            await ctx.guild.vanity_invite()
            or await ctx.channel.create_invite(
                reason="Rocationに登録する招待リンクの作成のため。"
            )
        ).url

    @rocations.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_(self, ctx: Context):
        if (elapsed := (now := time()) - self.data[ctx.guild.id].get("raised", 0.0)) > RAISE_TIME:
            self.data[ctx.guild.id].raised = now
            await ctx.reply("Raised! 表示順位をあげました。\n※数秒後反映されます。")
        else:
            await ctx.reply(f"まだRaiseできません！\n<t:{int(RAISE_TIME-elapsed)}:R>にRaiseができるようになります。")

    @commands.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_alias(self, ctx: Context):
        await self.raise_(ctx)


def setup(bot):
    bot.add_cog(Rocations(bot))