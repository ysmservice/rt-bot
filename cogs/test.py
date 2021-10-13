# RT - Setting API Test

from discord.ext import commands, easy
import discord

from rtlib.slash import Option


class SlashTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(slash_command=True, description="スラッシュテスト用コマンド")
    async def test(
            self, ctx,
            arg1: Option(str, "arg1", "test_arg1"),
            arg2: Option(int, "arg2", "test_arg2"),
            arg3: Option(
                str, "arg3", "test_arg3",
                choices=(("1", "1"), ("2", "2"), ("3", "3"))
            ),
            arg4: Option(
                discord.Member, "arg4", "test_arg4", required=False
            ),
            arg5: str = "arg5 is nothing"
        ):
        await ctx.interaction.response.send_message(
            f"test {arg1} {arg2} {arg3} {arg4} {arg5}"
        )

    async def callback(self, view, interaction):
        await interaction.response.send_message("Hey")

    @commands.command()
    async def test_view(self, ctx):
        view = easy.View("TestEasyView")
        view.add_item(discord.ui.Button, self.callback, label="Don't touch me!")
        await ctx.reply("`discord.ext.easy.View` test", view=view())


def setup(bot):
    bot.add_cog(SlashTest(bot))
