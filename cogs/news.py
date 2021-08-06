# RT - News

from discord.ext import commands
import discord

from aiofiles import open as async_open
from ujson import loads, dumps
from typing import Optional
from time import time

from rtlib.ext import Embeds
from data import is_admin


class News(commands.Cog):
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data
        self.bot.add_listener(self._on_ready, "on_ready")

    async def _on_ready(self):
        self.db = await self.rt["mysql"].get_database()
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(
                "news", {"time": "FLOAT", "content": "TEXT"})

    async def _add_news(self, content: str) -> float:
        # Newsを新しく追加します。
        async with self.db.get_cursor() as cursor:
            await cursor.insert_data("news", {"time": (now := time()), "content": content})
        return now

    async def _remove_news(self, time_: int) -> None:
        # Newsを削除します。
        async with self.db.get_cursor() as cursor:
            await cursor.delete_data("news", {"time": time_})

    async def _get_news(self, time_: Optional[int] = None) -> Optional[str]:
        # Newsを取得する。
        async with self.db.get_cursor() as cursor:
            if time_ is None:
                return (await cursor.get_data("news", {"time": time_}))[0]

    async def _get_news_all(self) -> str:
        # Newsを全て取得する。
        async with self.db.get_cursor() as cursor:
            async for row in cursor.get_datas("news", {}):
                if row:
                    yield row[1]

    def convert_embed(self, doc: str) -> discord.Embed:
        # マークダウンをEmbedにする。
        title = doc[:(i := doc.find("\n"))]
        description = doc[i:(i := doc.find("## "))]
        embed = discord.Embed(
            title=title[2:] if title.startswith("# ") else title,
            description=description
        )
        values = doc[i:].replace("### ", "**#** ").split("## ")
        for value in values:
            if value:
                name = value[:(i := value.find("\n"))]
                name = "‌\n" + name
                embed.add_field(name=name, value=value[i:], inline=True)
        return embed

    @commands.group(
        extras={
            "headding": {
                "en": "Show RT's news.",
                "ja": "RTのニュースを表示します。"
            },
            "parent": "RT"
        }
    )
    async def news(self, ctx):
        """!lang ja
        --------
        最新のニュースを表示します。

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            embeds, i = Embeds("News"), 0
            async for content in self._get_news_all():
                i += 1
                print(content)
                embed = self.convert_embed(content)
                embed.title = f"{i} {embed.title}"
                embeds.add_embed(embed)
                if i == 10:
                    break
            if embeds.embeds == []:
                await ctx.reply("Newsは現在空です。")
            else:
                await ctx.reply(embeds=embeds)

    @news.command()
    @is_admin()
    async def add(self, ctx, *, content):
        """!lang ja
        --------
        ニュースに新しくなにかを追加します。  
        ※管理者用コマンドよって英語説明は不要です。

        Parameters
        ----------
        content : str
            ニュースに追加する文字列です。"""
        now = await self._add_news(content)
        await ctx.reply(f"Ok number:{now}")

    @news.command()
    @is_admin()
    async def remove(self, ctx, now: float):
        """!lang ja
        --------
        now : float
            削除するニュースの時間です。"""
        await self._remove_news(now)
        await ctx.reply("Ok")


def setup(bot):
    bot.add_cog(News(bot))
