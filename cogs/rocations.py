# RT - rocations

from __future__ import annotations

from typing import TypeVar, TypedDict, Optional

from collections import OrderedDict
from functools import wraps
from time import time

from discord.ext import commands
import discord

from aiomysql import Pool, Cursor

from rtlib.slash import UnionContext
from rtlib import RT


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
    language: str


RAISE_TIME = 14106 # 3時間55分06秒
Servers = OrderedDict[int, Server]


# 何か必要なもの
CheckFT = TypeVar("CheckFT")
def check(function: CheckFT) -> CheckFT:
    "宣伝が有効になっているか"
    @wraps(function)
    async def new(self: Rocations, ctx: UnionContext, *args, **kwargs):
        await ctx.trigger_typing()
        try:
            return await function(self, ctx, *args, **kwargs)
        except Exception as e:
            await ctx.reply(
                {"ja": f"エラーが発生しました。\nサーバーを登録をしていますか？\nErrorCode: `{e}`",
                 "en": f"An error has occurred.\nAre you registering a server? \nErrorCode: `{e}`."}
            )
    return new


# ほんへ
class Rocations(commands.Cog):

    TABLE = "Rocations"

    def __init__(self, bot: RT):
        self.bot = bot
        self.pool: Pool = self.bot.mysql.pool

        self.bot.loop.create_task(
            self._prepare_table(), name="Create Rocations table"
        )

    async def _prepare_table(self):
        # テーブルの準備をする。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                        GuildID BIGINT PRIMARY KEY NOT NULL, description TEXT, tags JSON,
                        nices JSON, invite TEXT, raised FLOAT, language TEXT
                    );"""
                )

    @commands.group(aliases=("rocal", "サーバー掲示板"))
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def rocations(self, ctx: UnionContext):
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    async def _exists(self, cursor: Cursor, guild_id: int) -> bool:
        # 渡されたサーバーIDのRocationが存在するかどうかをチェックします。
        await cursor.execute(
            f"SELECT GuildID FROM {self.TABLE} WHERE GuildID = %s;",
            (guild_id,)
        )
        return bool(await cursor.fetchone())

    def _assert_description(self, description):
        assert len(description) <= 2000, "文字数が多すぎます。"

    async def _get_invite(self, ctx: UnionContext):
        # 招待リンクを取得します。
        try: return (await ctx.guild.vanity_invite()).url
        except discord.Forbidden:
            return (await ctx.channel.create_invite(
                reason="Rocationに登録する招待リンクの作成のため。"
            )).url

    @rocations.command(aliases=("登録", "reg", "add"))
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def register(self, ctx: UnionContext, *, description):
        await ctx.trigger_typing()
        self._assert_description(description)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if await self._exists(cursor, ctx.guild.id):
                    await ctx.reply({
                        "ja": "既に設定されています。", "en": "Already exists."
                    })
                else:
                    await cursor.execute(
                        f"INSERT INTO {self.TABLE} VALUES (%s, %s, %s, %s, %s, %s, %s);",
                        (ctx.guild.id, description, "[]", "[]",
                         await self._get_invite(ctx), time(),
                         self.bot.cogs["Language"].get(ctx.guild.id))
                    )
                    await ctx.reply("Ok")

    @rocations.command(aliases=("del", "rm", "remove", "削除"))
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def delete(self, ctx: UnionContext):
        await ctx.trigger_typing()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if await self._exists(cursor, ctx.guild.id):
                    await cursor.execute(
                        f"DELETE FROM {self.TABLE} WHERE GuildID = %s;", (ctx.guild.id,)
                    )
        await ctx.reply("Ok")

    async def _update(self, query: str, args: tuple = ()):
        # 更新を行います。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query.replace("<t>", self.TABLE), args)

    @rocations.command()
    @check
    async def tags(self, ctx: UnionContext, *, tags: str):
        assert (tags := tags.split("/")) <= 10, {"ja": "多すぎます。", "en": "I can't set it up that well."}
        await self._update(
            "UPDATE <t> SET tags = %s WHERE GuildID = %s;", (tags, ctx.guild.id)
        )
        await ctx.reply("Ok")

    @rocations.command()
    @check
    async def description(self, ctx: UnionContext, *, description: str):
        self._assert_description(description)
        await self._update(
            "UPDATE <t> SET description = %s WHERE GuildID = %s;", (
                description, ctx.guild.id
            )
        )
        await ctx.reply("Ok")

    @rocations.command()
    @commands.cooldown(1, 180, commands.BucketType.guild)
    async def invite(self, ctx: UnionContext):
        await self._update(
            "UPDATE <t> SET invite = %s WHERE GuildID = %s;", (
                await self._get_invite(ctx), ctx.guild.id
            )
        )
        await ctx.reply("Ok")

    @rocations.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_(self, ctx: UnionContext):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT raised FROM {self.TABLE} WHERE GuildID = %s;",
                    (ctx.guild.id,)
                )
                raised = (await cursor.fetchone())[0]
                if (elapsed := (now := time()) - raised) > RAISE_TIME:
                    await cursor.execute(
                        f"UPDATE {self.TABLE} SET raised = %s WHERE GuildID = %s;",
                        (now, ctx.guild.id)
                    )
                    await ctx.reply({
                        "ja": "Raised! 表示順位をあげました。",
                        "en": "Raised! I raised the display rank."
                    })
                else:
                    await ctx.reply({
                        "ja": f"まだRaiseできません！\n<t:{elapsed:=int(RAISE_TIME-elapsed)}:R>にRaiseができるようになります。",
                        "en": f"Can't Raise yet!\nYou will be able to Raise when the time is <t:{elapsed}:R>."
                    })

    @commands.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_alias(self, ctx: UnionContext):
        await self.raise_(ctx)


def setup(bot):
    bot.add_cog(Rocations(bot))