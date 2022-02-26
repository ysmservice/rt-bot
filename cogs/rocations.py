# RT - rocations

from __future__ import annotations

from typing import TypeVar, TypedDict, Optional

from collections import OrderedDict
from functools import wraps
from time import time

from discord.ext import commands
import discord

from aiomysql import Pool, Cursor
from ujson import dumps

from rtlib.slash import Context, UnionContext
from rtlib import RT


# データ型等
class Server(TypedDict):
    description: str
    tags: list[str]
    invite: str
    nices: dict[str, Optional[str]]
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
            if ctx.bot.test or isinstance(e, AssertionError): raise
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
                        nices JSON, invite TEXT, raised BIGINT, language TEXT
                    );"""
                )

    @commands.group(aliases=("rocal", "サーバー掲示板"))
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def rocations(self, ctx: UnionContext):
        if not ctx.invoked_subcommand:
            await ctx.reply({"ja": "使用方法が違います。", "en": "It's wrong way to use this command."})

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
                        (ctx.guild.id, description, "[]", r"{}",
                         await self._get_invite(ctx), int(time()),
                         self.bot.cogs["Language"].get(ctx.guild.id))
                    )
                    await ctx.reply(embed=discord.Embed(
                        title="Rocations", description={
                            "ja": f"公開しました。\nhttps://rt-bot.com/rocations?search={ctx.guild.id}",
                            "en": f"Published!\nhttps://rt-bot.com/rocations?search={ctx.guild.id}"
                        }, color=self.bot.Colors.normal
                    ).set_footer(text={
                        "ja": "Tips: サーバーの表示順位は3時間55分06秒に一度`/raise`で上げられるよ。",
                        "en": "Tips: You can use `/raise` to raise the server's display order once every 3 hours, 55 minutes, and 06 seconds."
                    }))

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
        assert len(tags := tags.split(",")) <= 7, {"ja": "多すぎます。", "en": "I can't set it up that well."}
        assert all(len(tag) <= 25 for tag in tags), {"ja": "タグは25文字以内にしてください。", "en": "Tags should be no longer than 25 characters."}
        await self._update(
            "UPDATE <t> SET tags = %s WHERE GuildID = %s;", (dumps(tags), ctx.guild.id)
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
        await ctx.trigger_typing()
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
                        (int(now), ctx.guild.id)
                    )
                    await ctx.reply({
                        "ja": "Raised! 表示順位をあげました。",
                        "en": "Raised! I raised the display rank."
                    })
                else:
                    await ctx.reply({
                        "ja": f"まだRaiseできません！\n<t:{(elapsed:=int(time()+(RAISE_TIME-elapsed)))}:R>にRaiseができるようになります。",
                        "en": f"Can't Raise yet!\nYou will be able to Raise when the time is <t:{elapsed}:R>."
                    })

    @commands.command("raise")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check
    async def raise_alias(self, ctx: UnionContext):
        await self.raise_(ctx)

    @discord.slash_command("raise", description="Rocationsでのサーバー表示順位を上げます。")
    async def raise_slash(self, interaction: discord.Interaction):
        await self.raise_(Context(self.bot, interaction, self.raise_alias, "rt!raise"))


def setup(bot):
    bot.add_cog(Rocations(bot))
