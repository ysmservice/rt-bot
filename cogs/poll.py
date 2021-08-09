# RT - Poll (Vote)

from discord.ext import commands
import discord

from typing import Callable, Tuple, List
from emoji import UNICODE_EMOJI_ENGLISH


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data
        self.emojis = [chr(0x1f1e6 + i) for i in range(26)]

    @commands.command(
        extras={"headding": {"ja": "投票パネルを作成します。", "en": "..."},
                "parent": "ServerPanel"},
        aliases=["vote"]
    )
    @commands.cooldown(1, 8)
    async def poll(self, ctx, title, only_one: bool, *, content):
        """!lang ja
        --------
        投票パネルを作成します。
        
        Parameters
        ----------
        title : str
            投票パネルのタイトルです。
        only_one : bool
            投票を一人一つまでとします。
        content : str
            改行で分けた投票に入れる項目です。  
            行の最初に絵文字を置くとその絵文字が投票パネルに使われます。  
            もし絵文字を置かない場合は自動で英文字が割り振られます。

        Examples
        --------
        ```
        rt!poll 好きな人は？ on
        tasuren
        ミスティックガール
        吹雪ちゃん
        NYN姉貴
        野獣先輩
        ```
        好きな人を問う投票パネルを一人一票までとして作ります。
        
        !lang en
        --------
        上にあるものの英語版です。"""
        description, emojis = self.make_description(content)

        embed = discord.Embed(
            title=title,
            description=description,
            color=ctx.author.color
        )
        embed.set_author(
            icon_url=ctx.author.avatar.url,
            name=ctx.author.display_name
        )
        embed.set_footer(text="[...]")
        mes = await ctx.send(
            "RT投票パネル" + " (一人一票)" if only_one else "",
            embed=embed, replace_language=False
        )
        for emoji in emojis:
            await mes.add_reaction(emoji)

    def make_description(self, content: str, on_integer: Callable = None) -> Tuple[str, List[str]]:
        # 渡された情報から投票パネルの説明に入れる文字列を作成する。
        description, i, emojis, emoji = "", -1, [], ""
        index, did = int(on_integer is not None), False

        for line in content.splitlines():
            if line:
                # もし初期状態の作成時ではないならindexを0じゃないのに変更しておく。
                if index and not did:
                    index = line.find("` ") + 2
                    did = True

                i += 1
                # 絵文をを取り出す。絵文字がないなら絵文字を用意する。
                if line[index] == "<" and ">" in line and line.count(":") > 1:
                    # もし外部絵文なら。
                    emojis.append(line[:line.find(">") + 1])
                elif line[index] in UNICODE_EMOJI_ENGLISH:
                    # もし普通の絵文字なら。
                    emojis.append(line[index])
                elif line[index] == self.emojis[i]:
                    emojis.append(line[index])
                else:
                    # もし絵文字がないなら作る。(ABCの絵文字。)
                    emojis.append((emoji := self.emojis[i]))
                    line = emoji + " " + line

                description += (f"`{0 if on_integer is None else on_integer(emojis[-1])}` "
                                + line[index:] + "\n")
        del content, i, emoji
        return description, emojis

    def check_panel(self, payload) -> bool:
        # RTの投票パネルか確認するための関数です。
        return (any(str(payload.emoji) == str(reaction.emoji) for reaction in payload.message.reactions)
                and payload.message.content.startswith("RT投票パネル") and not payload.member.bot
                and payload.message.guild and payload.message.embeds
                and payload.message.author.id == self.bot.user.id)

    def graph(self, p: dict, size: int = 35) -> str:
        # グラフを作るための関数です。
        r, t = '[', len(p)

        for n in list(p.keys()):
            p[n] = int(p[n] / t * size)
            if p[n] % 2 == 0:
                p[n] += 1

            if p[n] > 1:
                r += '<'
            if p[n] > 3:
                r += '=' * int((p[n] - 3 if p[n] - 3 > 0 else 0) / 2)
            r += n
            if p[n] > 3:
                r += '=' * int((p[n] - 3) / 2)
            if p[n] > 1:
                r += '>'
        return r + ']'

    async def update_panel(self, payload):
        # もし一人一票までで既に投票しているならreturnして投票パネルのアップデートをしない。
        if "一" in payload.message.content:
            users = len([reaction for reaction in payload.message.reactions
                         if any(user.id == payload.member.id
                                for user in await reaction.users().flatten())])
            if users > 1:
                return
        # RTの投票パネルをアップデートする。
        embed = payload.message.embeds[0]
        emojis = {str(reaction.emoji): reaction.count - 1
                  for reaction in payload.message.reactions}
        # 最大桁数を数える。
        before = 1
        for key in emojis:
            if before < (now := len(str(emojis[key]))):
                before = now
        # Embedを編集する。
        description, _ = self.make_description(
            embed.description, lambda emoji: str(emojis[emoji]).zfill(before)
        )
        embed.description = description
        embed.set_footer(text=self.graph(emojis))
        await payload.message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload):
        if self.bot.is_ready():
            if self.check_panel(payload):
                await self.update_panel(payload)

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload):
        if self.bot.is_ready():
            if self.check_panel(payload):
                await self.update_panel(payload)


def setup(bot):
    bot.add_cog(Poll(bot))