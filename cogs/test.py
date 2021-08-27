# RT - Setting API Test

from discord.ext import commands
import discord

from rtlib.slash import Option


class SlashTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(slash_command=True)
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


def setup(bot):
    bot.add_cog(SlashTest(bot))
