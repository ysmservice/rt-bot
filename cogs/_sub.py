# RT Chan - Info

from discord.ext import commands
import discord


INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=888635684552863774&permissions=172339022401&scope=bot%20applications.commands"
DESCRIPTION = f"""[Discordの多機能BotであるRT](https://rt-bot.com/)の音楽再生と読み上げだけ使えるようにしたサブBotのりつだよ！
多機能BotのRTは音楽再生や読み上げの他にもサーバーステータスやいつも下に来るメッセージなど様々な機能があるよ！([詳細はここへ](https://rt-bot.com))
私をサーバーに招待したい人は[ここ]({INVITE_URL})をクリック！"""


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        slash_command=True, aliases=["info", "about", "招待"],
        description="りつたんの招待リンク/情報を表示します。"
    )
    async def invite(self, ctx):
        await ctx.reply(
            embed=discord.Embed(
                title="りつたん",
                description=DESCRIPTION,
                color=self.bot.colors["normal"]
            )
        )

    @commands.command(
        slash_command=True, aliases=["h", "へるぷ", "ヘルプ"],
        description="りつたんの操作方法を表示します。"
    )
    async def help(self, ctx):
        await ctx.reply(
            ("音楽再生のヘルプ：https://rt-bot.com/help.html?g=music\n"
             "読み上げのヘルプ：https://rt-bot.com/help.html?g=entertainment&c=tts\n"
             "このBotについて/招待リンク：`rt#info` (初めての方は読むのを推奨します。)\n"
             "このBotのプリフィックスは`rt!`ではありません！\n上のヘルプには`rt!`とありますがそれは違う方です。\n"
             "なお`りつちゃん `や`りつたん `のプリフィックスでも呼べます。\n"
             "そしてスラッシュコマンドに対応しています。")
        )

    @commands.Cog.listener()
    async def on_full_ready(self):
        await self.bot.change_presence(
            activity=discord.Activity(
                name="rt#help | 少女絶賛稼働中！",
                type=discord.ActivityType.watching, state="りつたん"
            )
        )


def setup(bot):
    bot.add_cog(Info(bot))