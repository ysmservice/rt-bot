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
                "news", {"time": "BIGINT", "content": "TEXT"})

    async def _add_news(self, content: str) -> None:
        # Newsを新しく追加します。
        async with self.db.get_cursor() as cursor:
            await cursor.insert_data("news", {"time": time(), "content": content})

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
                    yield row[0]

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
        embeds = Embeds("News")
        async for row in self._get_news_all():
            embeds.add_embed()


def setup(bot):
    bot.add_cog(News(bot))
