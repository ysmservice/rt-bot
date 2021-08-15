# RT - Person

from discord.ext import commands
import discord

from datetime import timedelta
from rtlib.ext import Embeds


class Person(commands.Cog):

    EMOJIS = {
        "UserFlags.hypesquad_bravery": "<:HypeSquad_Bravery:795129521140793384>",
        "UserFlags.hypesquad_brilliance": "<:HypeSquad_Brilliance:795129460709785601>",
        "UserFlags.hypesquad_balance": "<:HypeSquad_Balance:795129576661581864>"
    }

    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        extras={
            "headding": {"ja": "指定されたユーザーIDまたはユーザー名からユーザー情報を取得します。",
                         "en": ""},
            "parent": "Individual"
        },
        aliases=["ui", "search_user", "ゆーざーいんふぉ！", "<-これかわいい！"]
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(self, ctx, *, user_name_id = None):
        """!lang ja
        --------
        指定されたユーザーの名前またはユーザーIDからユーザー情報を取得します。  
        ※ユーザー名の場合はRTが入っている何かしらのサーバーにいるユーザーでないと取得はできません。

        Parameters
        ----------
        user : ユーザーIDまたはユーザー名
            見たいユーザー情報のユーザーのIDまたは名前です。

        Aliases
        -------
        ui, search_user, ゆーざーいんふぉ！, <-これかわいい！

        Examples
        --------
        `rt!userinfo tasuren`"""
        await ctx.trigger_typing()
        # もしuser_name_idが指定されなかった場合は実行者のIDにする。
        if user_name_id is None:
            user_name_id = ctx.author.id
        # ユーザーオブジェクトを取得する。
        try:
            user_id = int(user_name_id)
            user = None
        except ValueError:
            for guild in self.bot.guilds:
                user = discord.utils.get(guild.members, name=user_name_id)
                break
            member = discord.utils.get(ctx.guild.members, name=user_name_id)
        else:
            user = await self.bot.fetch_user(user_id)
            member = ctx.guild.get_member(user_id)

        if user:
            # ユーザー情報のEmbedを作る。
            embeds = []
            bot = (f" **`{'✅' if user.public_flags.verified_bot else ''}BOT`**"
                   if user.bot else "")
            embed = discord.Embed(
                title=f"{user}{bot}",
                description="".join(
                    self.EMOJIS.get(str(flag), "")
                    for flag in user.public_flags.all()
                ) if user.public_flags else "",
                color=self.bot.colors["normal"]
            )
            embed.set_thumbnail(url=user.avatar.url)
            embed.add_field(name="ID", value=f"`{user.id}`")
            embed.add_field(
                name={
                    "ja": "Discord登録日時",
                    "en": "..."
                },
                value=(user.created_at + timedelta(hours=9)
                ).strftime('%Y-%m-%d %H:%M:%S')
            )
            embeds.append(embed)
            # サーバーのユーザー情報のEmbedを作る。
            if member:
                embed = discord.Embed(
                    title={
                        "ja": "このサーバーでの情報",
                        "en": "..."
                    },
                    description=(
                        "@everyone, "+ ", ".join(
                        role.mention for role in member.roles
                        if role.name != "@everyone")
                    ),
                    color=member.color
                )
                embed.add_field(
                    name={"ja": "表示名",
                          "en": "..."},
                    value=member.display_name
                )
                embed.add_field(
                    name={"ja": "参加日時",
                          "en": "..."},
                    value=(member.joined_at + timedelta(hours=9)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                )
                if member.voice:
                    embed.add_field(
                        name={"ja": "接続中のボイスチャンネル",
                            "en": "..."},
                        value=f"<#{member.voice.channel.id}>"
                    )
                embeds.append(embed)
            # 作ったEmbedを送信する。
            for embed in embeds:
                await ctx.send(embed=embed)
            del embeds, embed
        else:
            # 見つからないならエラーを発生させる。
            raise commands.errors.UserNotFound(
                "そのユーザーの情報が見つかりませんでした。"
            )


def setup(bot):
    bot.add_cog(Person(bot))