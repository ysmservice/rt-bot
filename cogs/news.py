# RT - News

from discord.ext import commands
import discord

from sanic.response import json
from datetime import datetime
from time import time

from data import is_admin, get_headers
from rtlib import DatabaseManager
from rtlib.ext import Embeds


class DataManager(DatabaseManager):
    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            "news", {
                "id": "BIGINT", "time": "TEXT",
                "content": "TEXT", "image": "TEXT"
            }
        )

    async def add_news(self, cursor, content: str, image: str) -> float:
        # Newsを新しく追加します。
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        t = int(time())
        await cursor.insert_data(
            "news", {"id": t, "time": now, "content": content, "image": image}
        )
        return t

    async def remove_news(self, cursor, id_: int) -> None:
        # Newsを削除します。
        await cursor.delete("news", {"id": id_})

    async def get_news(self, cursor, id_: int) -> tuple:
        # Newsを取得する。
        return (await cursor.get_data("news", {"id": id_}))

    async def get_news_all(self, cursor) -> list:
        # Newsを全て取得する。
        return [row async for row in cursor.get_datas(
                "news", {}, custom="ORDER BY id DESC")
                if row]


class News(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data
        self.bot.loop.create_task(self._on_ready())

    async def _on_ready(self):
        super(commands.Cog, self).__init__(self.bot.mysql)
        await self.init_table()

    async def get_rows(self) -> list:
        return reversed(await self.get_news_all())

    @commands.Cog.route("/news/<number>")
    async def news_api(self, request, number=None) -> None:
        rows = await self.get_rows()
        if number:
            rows = list(rows)
            row = rows[int(number)]
            data = {
                "content": row[2], "date": row[1],
                "status": "ok", "title": row[2][:row[2].find("\n") + 1]
            }
        else:
            data = {
                str(i): [row[2][:row[2].find("\n") + 1], row[1]]
                for i, row in enumerate(rows)
            }
            data["status"] = "ok"
        return json(data, headers=get_headers(self.bot, request))

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
        `rt!news`だけでいいです。  
        下にあるadd/removeはRT管理者のみ実行可能です。

        !lang en
        --------
        Show RT's news."""
        if not ctx.invoked_subcommand:
            embeds, i = Embeds("News", ctx.author.id), 0
            for row in await self.get_news_all():
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

        Parameters
        ----------
        image : str
            写真のURLです。  
            写真がないのなら`None`を入れてください。
        content : str
            ニュースに追加する文字列です。"""
        now = await self.add_news(content, image)
        await ctx.reply(f"Ok number:{now}")

    @news.command()
    @is_admin()
    async def remove(self, ctx, id_: int):
        """!lang ja
        --------
        ニュースを削除します。

        Parameters
        ----------
        id : int
            削除するニュースのidです。"""
        await self.remove_news(id_)
        await ctx.reply("Ok")


def setup(bot):
    bot.add_cog(News(bot))
