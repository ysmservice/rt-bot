# RT - YouTubeTogether

from discord.ext import commands
import discord

from rtlib.slash import Option


class YouTubeTogether(commands.Cog):

    APPLICATIONS = {
        "youtube": "755600276941176913",
        "poker": "755827207812677713",
        "betrayal": "773336526917861400",
        "fishing": "814288819477020702",
        "chess": "832012774040141894"
    }

    BASE_INVITE = "https://discord.gg/"

    def __init__(self, bot):
        self.bot = bot

    async def make_invite(
        self, voice_channel_id: int, appid: str,
        *, max_age: int = 0, max_uses: int = 0
    ) -> str:
        """!lang ja
        --------
        アクティビティ招待リンクを作ります。  
        使えるアクティビティは`YouTubeTogether.APPLICATIONS`に辞書形式であります。  
        そこにないアクティビティがある際は自分で追加してください。

        Parameters
        ----------
        voice_channel_id : int
            対象のボイスチャンネルのIDです。
        appid : str
            対象のアクティビティのIDです。  
            `YouTubeTogether.APPLICATIONS`にあります。
        max_age : int, default 0
            招待リンクが何秒有効かです。
        max_uses : int, default 0
            最大使用回数です。"""
        return self.BASE_INVITE + (
            await self.bot.http.request(
                discord.http.Route(
                    "POST", f"/channels/{voice_channel_id}/invites",
                ), json={
                    "max_age": max_age,
                    "max_uses": max_uses,
                    "target_application_id": appid,
                    "target_type": 2,
                    "temporary": False,
                    "validate": None
                }
            )
        )["code"]

    @commands.command(
        slash_command=True,
        description="YouTube Togetherなどの招待リンクを作ります。"
    )
    async def activity(
        self, ctx, choice: Option(
            str, "activity", "作る招待リンクのアクティビティの名前です。",
            choices=tuple((key, key) for key in APPLICATIONS)
        )
    ):
        if (appid := self.APPLICATIONS.get(choice)):
            if ctx.author.voice:
                await ctx.reply(
                    await self.make_invite(
                        ctx.author.voice.channel.id, appid,
                    )
                )
            else:
                await ctx.reply(
                    {"ja": "ボイスチャンネルに接続してください。",
                     "en": "Please connect to voice channel."}
                )
        else:
            await ctx.reply(
                {"ja": "そのアクティビティはありません。",
                 "en": "The activity is not found."}
            )


def setup(bot):
    bot.add_cog(YouTubeTogether(bot))