# RT - Language

from discord.ext import commands
import discord

from aiofiles import open as async_open
from typing import Literal, Union
from ujson import loads
from copy import copy

from data import is_admin


class Language(commands.Cog):
    """# Language
    ## このコグの内容
    * 言語設定コマンド。
       - self.language
    * IDからそのIDになんの言語が設定されているかを取得する関数。
       - self.get
    * 言語データのリロード。
       - self.reload_language / self.update_language
    * send呼び出し時にもし実行者/サーバーが英語に設定しているなら、contentなどを言語データから英語のものに置き換えるようにsendを改造する。
       - self.dpy_injection"""

    LANGUAGES = ("ja", "en")

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.db = self.botdata["mysql"]
        self.dpy_injection()

    def dpy_injection(self):
        # discord.pyのsendを改造する。
        default_send = copy(discord.abc.Messageable.send)

        async def new_send(channel, *args, **kwargs):
            # 元のsendにつけたしをしたバージョンのsend。
            # このsendが返信に使われたのなら返信先のメッセージの送信者(実行者)の言語設定を読み込む。
            lang = "ja"
            if (reference := kwargs.get("reference")) is not None:
                lang = self.get(reference.author.id)
            # もし実行者の言語設定がjaじゃないならcontentなどの文字列が言語データにないか検索をする。
            if lang != "ja":
                if (content := kwargs.get("content", False)):
                    # contentを翻訳済みに交換する。
                    kwargs["content"] = self.replace_language()
                if kwargs.get("embed", False):
                    kwargs["embed"] = self.replace_language()
                    
            return await default_send(
                channel.channel if isinstance(channel, commands.Context) else channel,
                *args, **kwargs
            )

        discord.abc.Messageable.send = self.new_send

    def replace_language(self, content: Union[str, discord.Embed], language: Literal[LANGUAGES]) -> Union[str, discord.Embed]:
        """渡されたものにある文字列を渡された言語コードのものに交換をします。  
        渡されたものにある文字列は渡された言語コードと一緒にdata/replies.jsonにないと変化しません。

        Parameters
        ----------
        content : Union[str, discord.Embed]
            交換をするもの。
        language : Literal["ja", "en"]
            交換先の言語コードです。

        Returns
        -------
        Union[str, discord.Embed] : contentにある文字列をlanguageに対応する文字列に交換した後のcontentです。"""
        pass

    def get_text(self, author_id: int, text: str) -> str:
        """textを渡されたIDに設定されている言語コードにあった文字列にして返します。  
        data/replies.jsonに翻訳済みのものがあるtextでなければ変化しません。

        Parameters
        ----------
        author_id : int
            対象のユーザーのIDです。
        text : str
            交換したい文字列です。"""
        return self.replies[self.get(author_id)].get(text, text)

    async def update_language(self) -> None:
        # 言語データを更新します。
        async with async_open("data/replies.json") as f:
            self.replies = loads(await f.read())

    @commands.command()
    @is_admin()
    async def reload_language(self, ctx):
        """言語データを再読込します。

        !parent Admin
        -------"""
        await ctx.trigger_typing()
        await self.update_language()
        await ctx.reply("Ok")

    async def update_cache(self, cursor):
        # キャッシュを更新します。
        # キャッシュがあるのはコマンドなど実行時に毎回データベースから読み込むのはあまりよくないから。
        async for ugid, lang in cursor.get_datas("language", {}):
            self.cache[ugid] = lang

    @commands.Cog.listener()
    async def on_ready(self):
        # テーブルがなければ作っておく。
        columns = {
            "id": "INTEGER",
            "language": "TEXT"
        }
        async with self.db.get_cursor() as cursor:
            await cursor.create_table("language", columns)
            # キャッシュを更新しておく。
            await self.update_cache(cursor)
        # 言語データを読み込んでおく。
        await self.update_language()

    def get(self, ugid: int) -> Literal[LANGUAGES]:
        """渡されたIDになんの言語が設定されているか取得できます。  
        Bot起動後でないと正しい情報を取得することができないので注意してください。

        Parameters
        ----------
        ugid : int
            ユーザーIDまたはサーバーIDです。

        Returns
        -------
        Literal["ja", "en"] : 言語コード。"""
        return self.cache.get(ugid, "ja")

    @commands.command(aliases=["lang"])
    async def language(self, ctx, language: Literal[LANGUAGES]):
        """!lang ja
        --------
        RTの言語設定を変更します。

        Parameters
        ----------
        language : 言語コード, `ja`または`en`
            変更対象の言語コードです。  
            現在は日本語である`ja`と英語である`en`に対応しています。

        Raises
        ------
        ValueError : もし無効な言語コードが入れられた場合発生します。

        !lang en
        --------
        Change the language setting for RT.

        Parameters
        ----------
        language : Language code, `ja` or `en`
            Code for the language to change.  
            You can use the Japanese `ja` or the English `en`.

        Raises
        ------
        ValueError : Occurs if an invalid language code is inserted."""
        # 言語コードが使えない場合はValueErrorを発生する。
        if language not in self.LANGUAGES:
            code = "invalid language code is inserted. 無効な言語コードです。"
            raise ValueError(f"Error: {code}")

        # 返信内容と変更内容を用意する。
        color, mode = self.bot.colors["normal"], None
        title, description = "Ok", None
        await ctx.trigger_typing()

        # データベースに変更内容を書き込む。
        if mode is not None:
            targets = {"id": ctx.author.id}
            async with self.db.get_cursor() as cursor:
                new = {"language": language}
                if await cursor.exists("language", targets):
                    await cursor.update_data("language", new, targets)
                else:
                    targets.update(new)
                    await cursor.insert_data("language", targets)
                await self.update_cache(cursor)

        # 返信をする。
        embed = discord.Embed(
            title=title, description=description, color=color)
        await ctx.reply(embed)


def setup(bot):
    bot.add_cog(Language(bot))
