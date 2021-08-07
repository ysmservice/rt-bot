# RT - News

from discord.ext import commands
import discord

from aiofiles import open as async_open
from ujson import loads, dumps
from datetime import datetime
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
                "news", {"id": "BIGINT", "time": "TEXT",
                         "content": "TEXT", "image": "TEXT"})

    async def _add_news(self, content: str, image: str) -> float:
        # Newsを新しく追加します。
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        t = time()
        async with self.db.get_cursor() as cursor:
            await cursor.insert_data(
                "news", {"id": t, "time": now, "content": content, "image": image})
        return t

    async def _remove_news(self, id_: int) -> None:
        # Newsを削除します。
        async with self.db.get_cursor() as cursor:
            await cursor.delete_data("news", {"id": id_})

    async def _get_news(self, id_: int) -> tuple:
        # Newsを取得する。
        async with self.db.get_cursor() as cursor:
            return (await cursor.get_data("news", {"id": id_}))

    async def _get_news_all(self) -> tuple:
        # Newsを全て取得する。
        async with self.db.get_cursor() as cursor:
            async for row in cursor.get_datas("news", {}, custom="ORDER BY id DESC"):
                if row:
                    yield row

    def convert_embed(self, doc: str) -> discord.Embed:
        # マークダウンをEmbedにする。
        i = doc.find("\n")
        title = doc if i == -1 else doc[:i]
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
                embed.add_field(name=name, value=value[i:], inline=False)
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
            embeds, i = Embeds("News", ctx.author.id), 0
            async for row in self._get_news_all():
                i += 1
                embed = self.convert_embed(row[2])
                embed.title = f"{embed.title}"
                embed.set_footer(text=f"{row[1]} | ID:{row[0]}")
                if row[3] != "None":
                    embed.set_image(url=row[3])
                embeds.add_embed(embed)
                if i == 10:
                    break
            if embeds.embeds == []:
                await ctx.reply("Newsは現在空です。")
            else:
                await ctx.reply(content="**最新のRTニュース**", embeds=embeds)

    @news.command()
    @is_admin()
    async def add(self, ctx, image, *, content):
        """!lang ja
        --------
        ニュースに新しくなにかを追加します。  
        ※管理者用コマンドよって英語説明は不要です。

        Parameters
        ----------
        image : str
            写真のURLです。です。  
            写真がないのなら`None`を入れてください。
        content : str
            ニュースに追加する文字列です。"""
        now = await self._add_news(content, image)
        await ctx.reply(f"Ok number:{now}")

    @news.command()
    @is_admin()
    async def remove(self, ctx, id_: int):
        """!lang ja
        --------
        id : int
            削除するニュースのidです。"""
        await self._remove_news(id_)
        await ctx.reply("Ok")


def setup(bot):
    bot.add_cog(News(bot))
