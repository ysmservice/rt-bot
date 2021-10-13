# RT - Google Translator

from discord.ext import commands
import discord

from jishaku.functools import executor_function
from deep_translator import GoogleTranslator
from asyncio import sleep
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
    "en": ("Dedicated translation channel function", """# translation channel plugin - translate
This is a feature that allows you to make a channel dedicated to translation by putting `rt>translate <language code to translate to>` in the channel topic.  
Example: `rt>translate ja` (all messages sent to a channel with this in the topic will be translated into Japanese).  

### Language code example
```
Japanese `ja`  
English  `en`
```
Other codes can be found by looking up `<language name> code` or something like that.

### Alias
trans

### Also see
It's in the personal category with the `translate` command.""")
}


class Translator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_command_added())

    @executor_function
    def translate(self, text: str, target: str) -> str:
        return GoogleTranslator(target=target).translate(text)

    async def on_command_added(self):
        # ヘルプにチャンネルプラグイン版翻訳を追加するだけ。
        await sleep(1.5)
        for lang in CHP_HELP:
            self.bot.cogs["DocHelp"].add_help(
                "ChannelPlugin", "TranslateChannel",
                lang, *CHP_HELP[lang]
            )

    @commands.command(
        name="translate", aliases=["trans", "ほんやく", "翻訳"],
        extras={
            "headding": {"ja": "翻訳をします。", "en": "This can do translate."},
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
        trans, ほんやく, 翻訳

        See Also
        --------
        translate(チャンネルプラグイン) : 翻訳専用チャンネル機能。

        !lang en
        --------
        This can do translate.

        Parameters
        ----------
        lang : language code
            The language code for which language to translate.
            If you want use japanese you do `ja` and If you want to use English you do `en`.
        content : str
            Translate content

        Examples
        --------
        `rt!translate ja I wanna be the guy!`
        RT：男になりたい！

        Aliases
        -------
        trans

        See Also
        --------
        translate(channel plugin) : Only for translate channel."""
        await ctx.trigger_typing()
        await ctx.reply(
            embed=discord.Embed(
                title={"ja": "翻訳結果",
                       "en": "translate result"},
                description=await self.translate(content, lang),
                color=self.bot.colors["normal"]
            ).set_footer(
                text="Powered by Google Translate",
                icon_url="http://tasuren.syanari.com/RT/GoogleTranslate.png"
            )
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.Thread):
            return
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
