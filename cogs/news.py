# RT - News

from discord.ext import commands

from aiofiles import open as async_open
from ujson import loads, dumps
from time import time

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
        ...


def setup(bot):
    bot.add_cog(News(bot))
