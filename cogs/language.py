# RT - Language

from discord.ext import commands
from typing import Literal


class Language(commands.Cog):

    LANGUAGES = ("ja", "en")

    def __init__(self, bot):
        self.bot = bot
        self.cache = {
            "me": {},
            "guild": {}
        }
        self.db = self.botdata["mysql"]

    async def update_cache(self, cursor):
        # キャッシュを更新します。
        # キャッシュがあるのはコマンドなど実行時に毎回データベースから読み込むのはあまりよくないから。
        async for mode, ugid, lang in cursor.get_datas("language", {}):
            self.cache[mode][ugid] = lang

    @commands.Cog.listener()
    async def on_ready(self):
        # テーブルがなければ作っておく。
        columns = {
            "mode": "TEXT",
            "id": "INTEGER",
            "language": "TEXT"
        }
        async with self.db.get_cursor() as cursor:
            await cursor.create_table("language", columns)
            # キャッシュを更新しておく。
            await self.update_cache(cursor)

    def get(self, mode: Literal["me", "guild"], ugid: int) -> Literal[LANGUAGES]:
        """渡されたIDになんの言語が設定されているか取得できます。  
        Bot起動後でないと正しい情報を取得することができないので注意してください。

        Parameters
        ----------
        mode : Literal["me", "guild"]
            ユーザーに設定されている言語設定かサーバーに設定されている言語設定どっちか。
        ugid : int
            ユーザーIDまたはサーバーIDです。

        Returns
        -------
        Literal["ja", "en"] : 言語コード。"""
        return self.cache[mode].get(ugid, "ja")

    @commands.command(aliases=["lang"])
    async def language(self, ctx, language: Literal[LANGUAGES], me: bool = True):
        """!lang ja
        --------
        RTの言語設定を変更します。

        Parameters
        ----------
        language : 言語コード, `ja`または`en`
            変更対象の言語コードです。  
            現在は日本語である`ja`と英語である`en`に対応しています。
        me : on/off, default on
            自分が実行した時のみ言語が変わるようにするかどうかです。  
            これを`off`にすると実行したサーバー単位で言語設定がされます。  
            サーバー単位での設定は管理者権限が必要です。

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
        me : on/off
            Whether you want the language to change only when you run it.  
            If you set this to `off`, the language setting is set on a per-server basis.  
            Per-server configuration requires administrator privileges.

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
        if me:
            mode = "me"
            await ctx.trigger_typing()
        else:
            if ctx.author.guild_permissions.administrator:
                mode = "guild"
                await ctx.trigger_typing()
            else:
                title = "Failed"
                description = "You cant't run this command.\n"
                description += "あなたはこのコマンドを実行することができません。"
                color = self.bot.colors["error"]
        # データベースに変更内容を書き込む。
        if mode is not None:
            targets = {
                "mode": mode,
                "id": ctx.guild.id if mode == "guild" else ctx.author.id
            }
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
