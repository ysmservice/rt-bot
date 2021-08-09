# RT - Poll (Vote)

from discord.ext import commands

from emoji import UNICODE_EMOJI_ENGLISH
from typing import Callable


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data

    @commands.command(
        extras={"headding": {"ja": "投票パネルを作成します。", "en": "..."},
                "parent": "ServerPanel"},
        aliases=["vote"]
    )
    @commands.cooldown(1, 8)
    async def poll(self, ctx, title, *, content):
        """!lang ja
        --------
        投票パネルを作成します。
        
        Parameters
        ----------
        title : str
            投票パネルのタイトルです。
        content : str
            改行で分けた投票に入れる項目です。  
            行の最初に絵文字を置くとその絵文字が投票パネルに使われます。  
            もし絵文字を置かない場合は自動で英文字が割り振られます。

        Examples
        --------
        ```
        rt!poll 好きひ人は？
        tasuren
        ミスティックガール
        吹雪ちゃん
        NYN姉貴
        野獣先輩
        ```
        [上を実行した結果の画像]()
        
        !lang en
        --------
        上にあるものの英語版です。"""
        description = self.make_description(content)

        embed = discord.Embed(
            title=title,
            description=description,
            color=ctx.author.color
        )
        embed.set_author(
            icon=ctx.author.avatar.url,
            name=ctx.author.display_name
        )
        embed.set_footer(text="[...]")
        mes = await ctx.send(
            "RT投票パネル", embed=embed,
            replace_language=False
        )
        for emoji in emojis:
            await mes.add_reaction(emoji)

    def make_description(self, content: str, on_integer: Callable = None) -> str:
        # 渡された情報から投票パネルの説明に入れる文字列を作成する。
        description, i, emojis, emoji = "", -1, [], ""
        for line in content.splitlines():
            if line:
                i += 1
                # 絵文をを取り出す。絵文字がないなら絵文字を用意する。
                if line[0] == "<" and ">" in line and line.count(":") > 1:
                    # もし外部絵文なら。
                    emojis.append(line[:line.find(">") + 1])
                elif line[0] in UNICODE_EMOJI_ENGLISH:
                    # もし普通の絵文字なら。
                    emojis.append(line[0])
                else:
                    # もし絵文字がないなら作る。(ABCの絵文字。)
                    emojis.append((emoji := chr(0x1f1e6 + i)))
                    line = emoji + " " + line

                description += (f"`{0 if on_integer is None else on_integer(emojis[-1])}` "
                                + line + "\n")
        del content, i, emoji
        return description

    def check_panel(self, payload) -> bool:
        # RTの投票パネルか確認するための関数です。
        return (any(payload.emoji == reaction.emoji for reaction in payload.message.reactions)
                and "RT投票パネル" == payload.message.content
                and payload.message.guild and payload.message.embeds
                and payload.message.author.id == self.bot.user.id)

    async def update_panel(self, payload):
        # RTの投票パネルをアップデートする。
        embed = payload.message.embeds[0]
        emojis = {str(reaction.emoji): reaction.count
                  for reaction in payload.message.reaction}
        description = self.make_description(
            embed.description, lambda emoji: emojis[emoji]
        )

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload):
        if self.check_panel(payload):
            await self.update_panel(payload)

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload):
        if self.check_panel(payload):
            await self.update_panel(payload)


def setup(bot):
    bot.add_cog(Poll(bot))