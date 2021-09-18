# RT Chan - Info

from discord import commands
import discord


class Info(commands.Cog):

    INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=888635684552863774&permissions=172339022401&scope=bot%20applications.commands"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(slash_command=True, aliases=["info", "about"])
    async def invite(self, ctx):
        await ctx.reply(
            embed=discord.Embed(
                title="りつちゃん",
                description="""[Discordの多機能BotであるRT](https://rt-bot.com/)の音楽再生と読み上げだけ使えるようにしたサブBotのりつだよ！
多機能BotのRTは音楽再生や読み上げの他にもサーバーステータスやいつも下に来るメッセージなど様々な機能があるよ！
もし興味があるなら[ここ](https://rt-bot.com)にきて招待したりサポートサーバーに行ってみよう！
私はそのRTにある音楽再生と読み上げを同時に使用したいという人のために生まれたよ。
私をサーバーに招待したい人は[ここ](self.INVITE_URL)をクリック！"""
            )
        )

    @commands.command(slash_command=True, aliases=["h"])
    async def help(self, ctx):
        await ctx.reply(
            "音楽再生のヘルプ：https://rt-bot.com/help.html?g=music\n読み上げのヘルプ：https://rt-bot.com/help.html?g=entertainment&c=tts\nこのBotについて/招待リンク：`rt#info`"
        )
