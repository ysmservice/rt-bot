# RT - Help

from discord.ext import commands
import discord


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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


    @commands.command(aliases=["dhelp"])
    async def discord_help(self, ctx, *, word):
        """"""
        pass


def setup(bot):
    bot.add_cog(Help(bot))
