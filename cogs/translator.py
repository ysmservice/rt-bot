# RT - Google Translator

from discord.ext import commands
import discord

from jishaku.functools import executor_function
from google_translate_py import AsyncTranslator
from typing import List


CHP_HELP = {
    "ja": ("翻訳専用チャンネル機能。",
"""# 翻訳チャンネルプラグイン - translate
これは`rt>translate <翻訳先言語コード>`をチャンネルのトピックに入れることで翻訳専用チャンネルにすることのできる機能です。  
例：`rt>translate ja` (これをトピックに入れたチャンネルに送信したメッセージは全て日本語に翻訳されます。)  

### 言語コード例
日本語 `ja`  
英語　 `en`  
他は調べれば出るので`言語名 言語コード`とかで調べてください。

### エイリアス
trans, ほんやく, 翻訳

### これもあるよ
翻訳コマンドである`translate`で個人カテゴリーにあります。"""),
    "en": ("...", """...""")
}


class Translator(commands.Cog, AsyncTranslator):
    def __init__(self, bot):
        self.bot = bot
        super(commands.Cog, self).__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        # ヘルプにチャンネルプラグイン版翻訳を追加するだけ。
        for lang in CHP_HELP:
            self.bot.cogs["DocHelp"].add_help(
                "ChannelPlugin", "翻訳チャンネル",
                lang, *CHP_HELP[lang]
            )

    @commands.command(
        name="translate", aliases=["trans", "ほんやく", "翻訳"],
        extras={
            "headding": {"ja": "翻訳をします。", "en": "Translate"},
            "parent": "Individual"
        }
    )
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def translate_(self, ctx, lang, *, content):
        """!lang ja
        --------
        翻訳をします。

        Parameters
        ----------
        lang : 言語コード
            どの言語に翻訳するかの言語コードです。  
            例えば日本語にしたい場合は`ja`で、英語にしたい場合は`en`です。
        content : str
            翻訳する内容です。

        Examples
        --------
        `rt!translate ja I wanna be the guy!`
        RT：男になりたい！

        Aliases
        -------
        trans, ほんやく, ほんやく

        See Also
        --------
        translate(チャンネルプラグイン) : 翻訳専用チャンネル機能。

        !lang en
        --------
        ..."""
        await ctx.trigger_typing()
        await ctx.reply(
            embed=discord.Embed(
                title={"ja": "翻訳結果",
                       "en": "..."},
                description=await self.translate(content, "", lang),
                color=self.bot.colors["normal"]
            ).set_footer(
                text="Powered by Google Translate",
                icon_url="http://tasuren.syanari.com/RT/GoogleTranslate.png"
            )
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or not message.channel.topic:
            return

        for line in message.channel.topic.splitlines():
            if line.startswith(("rt>translate", "rt>tran", "rt>翻訳", "rt>ほんやく")):
                if 1 < len((splited := line.split())):
                    await self.translate_(
                        await self.bot.get_context(message),
                        splited[1], content=message.content
                    )
                break


def setup(bot):
    bot.add_cog(Translator(bot))