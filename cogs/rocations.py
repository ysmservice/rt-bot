# RT - rocations

from __future__ import annotations

from typing import TypeVar, TypedDict, Optional

from collections import OrderedDict
from functools import wraps
from time import time

from discord.ext import commands, tasks

from rtlib.slash import UnionContext
from rtlib import RT, Table


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
    name: str


class RocationsData(Table):
    __allocation__ = "Guild"
    description: str
    tags: list[str]
    invite: str
    nices: list[Nice]
    raised: float
RAISE_TIME = 14106 # 3時間55分06秒
Servers = OrderedDict[int, Server]
SIZE_PER_INDEX = 10


# 何か必要なもの
CheckFT = TypeVar("CheckFT")
def check(function: CheckFT) -> CheckFT:
    "宣伝が有効になっているか"
    @wraps(function)
    async def new(self: Rocations, ctx: UnionContext, *args, **kwargs):
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
        self.data = RocationsData(bot)
        self._sorted_cache: list[Servers] = []

        self.bot.rtc.set_event(self.get_rocations)
        self.bot.rtc.set_event(self.get_rocation)
        self._process_cache.start()

    @tasks.loop(seconds=10)
    async def _process_cache(self):
        # キャッシュを処理します。
        # 十個ずつRaisedされた順でサーバー一覧のキャッシュを作っていく。
        i, now, count = 0, OrderedDict(), 0
        for guild_id, data in sorted(
            list(self.data.to_dict().items()), key=lambda x: x[1].get("raised", 0.0)
        ):
            if "invite" in data and data.get("description"):
                now[guild_id] = data
                if guild := self.bot.get_guild(guild_id):
                    now[guild_id]["name"] = guild.name
                else:
                    del now[guild_id]
                    del self.data[guild_id]
                    continue
                i += 1
                if i == SIZE_PER_INDEX:
                    self._sorted_cache.insert(0, now)
                    now, i = OrderedDict(), 0
                count += 1
                if count == 50:
                    break
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
        try: return self._sorted_cache[page]
        except KeyError: ...

    @commands.group(aliases=("rocal", "サーバー掲示板"))
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def rocations(self, ctx: UnionContext):
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    @rocations.command()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def toggle(self, ctx: UnionContext):
        if ctx.guild.id in self.data:
            del self.data[ctx.guild.id]
            await ctx.reply("Offにしました。")
        else:
            self.data[ctx.guild.id].description = ""
            await ctx.reply("Onにしました。")

    @rocations.command()
    @check
    async def tags(self, ctx: UnionContext, *, tags: str):
        self.data[ctx.guild.id].tags = tags.split("/")
        await ctx.reply("Ok")

    @rocations.command()
    @check
    async def description(self, ctx: UnionContext, *, description: str):
        self.data[ctx.guild.id].description = description
        await ctx.reply("Ok")

    @rocations.command()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def invite(self, ctx: UnionContext):
        self.data[ctx.guild.id].invite = (
            await ctx.guild.vanity_invite()
            or await ctx.channel.create_invite(
                reason="Rocationに登録する招待リンクの作成のため。"
            )
        ).url
        await ctx.reply("Ok")

    @rocations.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_(self, ctx: UnionContext):
        if (elapsed := (now := time()) - self.data[ctx.guild.id].get("raised", 0.0)) > RAISE_TIME:
            self.data[ctx.guild.id].raised = now
            await ctx.reply("Raised! 表示順位をあげました。\n※数秒後反映されます。")
        else:
            await ctx.reply(f"まだRaiseできません！\n<t:{int(RAISE_TIME-elapsed)}:R>にRaiseができるようになります。")

    @commands.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_alias(self, ctx: UnionContext):
        await self.raise_(ctx)


def setup(bot):
    bot.add_cog(Rocations(bot))