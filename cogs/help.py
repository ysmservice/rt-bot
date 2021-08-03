# RT - Help

from discord.ext import commands
import discord

from typing import List, Tuple


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help = self.bot.cogs["DocHelp"].data
        try:
            pass
        except Exception as e:
            print(e)

    @commands.command()
    async def help(self, ctx, *, word):
        """!lang ja
        --------
        ウェブサイトのURLを返します。  
        Discordからhelpを見たい場合は`dhelp`を実行してください。

        Parameters
        ----------
        word : str, optional
            この引数を指定するとこの引数に入れた言葉で検索をかけるウェブサイトのURLを返します。

        See Also
        --------
        dhelp : Discord上でヘルプを閲覧します。

        !lang en
        --------
        This command returns the URL of the web page where you can see the RT help.  
        If you want help on Discord instead of the web, run `dhelp`.

        Parameters
        ----------
        word : str, optional
            Searches for help using the words in this argument.
 
        See Also
        --------
        dhelp : See help on Discord."""
        embed = discord.Embed(
            title="Helpが必要ですか？",
            description="http://0.0.0.0" if self.bot.test else "https://rt-bot.com/help",
            color=self.bot.data["colors"]["normal"]
        )
        await ctx.reply(embed=embed)

    def _convert_embed(self, command_name: str, doc: str, **kwargs) -> List[discord.Embed]:
        # rtlib.libs.DocParserでドキュメンテーションからマークダウンに変換された文字列をEmbedに変換する関数。
        now, text, embed, embeds, field_length = ["description", 0], "", None, [], 0
        for line in doc.splitlines():
            is_item = line.startswith("## ")
            if is_item:
                if now[0] == "description":
                    embed = discord.Embed(
                        title=f"**{command_name}**", description=text[:-1], **kwargs)
                now = ["field", len(embed.fields)]
            if now[0] == "field":
                if field_length == 25:
                    embeds.append(embed)
                    embed, now = None, ["description", 0]
                else:
                    embed.add_field(
                        name=f"‌\n**{line[3:]}**", value="", inline=True)
                    now[0] = "field_name"
            if now[0] == "field_name" and not is_item:
                if line.startswith("### "):
                    line = "**#** " + line[4:]
                if line.count("*") > 3 and ":" in line and line[2] != "#":
                    line = line.replace("**", "`")
                if line.endswith("  "):
                    line = line[:-2]
                embed.set_field_at(
                    now[1], name=embed.fields[now[1]].name,
                    value=embed.fields[now[1]].value + line + "\n")
            if embed is None:
                text += f"{line}\n"
        if field_length < 25 and embed is not None:
            embeds.append(embed)
        return embeds

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def test_help(self, ctx, category_name, command_name, lang="ja"):
        # ドキュメンテーションをマークダウンにしてEmbedにすることができているか確認するためのテスト用コマンド。
        embeds = self._convert_embed(
            command_name,
            self.help[category_name][command_name][lang]
        )
        for embed in embeds:
            await ctx.send(embed=embed)

    def search(self, word: str) -> Tuple[str, List[str], List[str]]:
        # 指定された言葉で検索またはヘルプの取得を行う関数です。
        # (完全一致の説明, 名前一部一致のリスト, 説明一部一致のリスト)で返されます。
        perfect, on_name, on_doc = "", [], []
        for category_name in self.help:
            perfect = self.help[category_name].get(word, "")
            if perfect != "":
                for cmd in self.help[category_name]:
                    if word in cmd:
                        on_name.append(cmd)
                    if word in self.help[category_name][cmd]:
                        on_doc.append(cmd)
            else:
                break
        return perfect, on_name, on_doc

    @commands.command(aliases=["dhelp"])
    async def discord_help(self, ctx, *, word: str = None):
        """!lang ja
        --------
        Discordからヘルプを閲覧します。

        Parameters
        ----------
        word : コマンド名/検索ワード, optional
            表示したいヘルプのコマンド名です。  
            コマンド名ではない言葉が指定された場合は検索します。

        !lang en
        --------
        上の英語バージョンをここに。"""
        if word is None:
            perfect, on_name, on_doc = self.search(word)
            embed = discord


def setup(bot):
    bot.add_cog(Help(bot))
