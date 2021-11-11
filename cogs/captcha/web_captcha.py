# RT - Captcha Web Manager

from typing import TYPE_CHECKING, TypedDict, Dict, Tuple

import discord

from time import time

if TYPE_CHECKING:
    from .__init__ import Captcha


class SuccessedUserData(TypedDict):
    guild_id: int
    user_id: int
    channel: discord.TextChannel


class WebCaptcha:
    def __init__(self, captcha_cog: "Captcha", secret: str):
        self.cog = captcha_cog
        self.secret: str = secret
        self.queue: Dict[str, Tuple[int, float, discord.TextChannel]] = {}
        self.base_url = (
            "http://localhost/"
            if self.cog.bot.test
            else "https://rt-bot.com/"
        )

    async def success_user(self, userdata: SuccessedUserData):
        "ユーザーの認証成功時の処理を実行する。"
        if ((guild := self.cog.bot.get_guild(userdata["guild_id"]))
                and (member := guild.get_member(userdata["user_id"]))):
            # 役職などを取得して役職を付与する。
            row = await self.cog.load(userdata["guild_id"])
            role = guild.get_role(row[3])

            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    result = (
                        "認証に失敗しました。"
                        "付与する役職がRTの役職より下にあるか確認してください。\n"
                        "Failed, make sure that the role position below the RT role position.\n"
                    )
                else:
                    result = (
                        "認証に成功しました。"
                        "役職が付与されました。\n"
                        "Success!"
                    )
                    self.cog.remove_cache(member)
            else:
                result = (
                    "役職が見つからないので役職を付与できませんでした。"
                    "すみません！！\n"
                    "Ah, I couldn't find the role to add to you."
                )
        else:
            result = (
                "あなたの所在がわからないため認証に失敗しました。"
            )
        await userdata["channel"].send(
            f"<@{userdata['user_id']}>, {result}"
        )

    async def captcha(
        self, channel: discord.TextChannel, member: discord.Member
    ) -> None:
        self.queue[f"{member.guild.id}-{member.id}"] = (member.id, time(), channel)
        embed = discord.Embed(
            title={"ja": "ウェブ認証", "en": "Web Captcha"},
            description={
                "ja": ("喋るには認証をしなければいけません。"
                    "\n認証を開始するには以下にアクセスしてください。\n"
                    f"Captcha URL : {self.base_url}captcha"
                    "\n※一時間放置されると無効になるので一時間放置した場合はサーバーに参加し直してください。"),
                "en": ("You must do authentication to speak."
                    "\nPlease access to that url to do authentication."
                    f"Captcha URL : {self.base_url}captcha"
                    "\n* If you leave it for an hour, it will become invalid, so if you leave it for an hour, please rejoin the server.")
            }, color=self.cog.bot.colors["normal"]
        )
        embed.set_footer(
            text="Powered by hCaptcha"
        )
        await channel.send(
            member.mention, embed=embed, target=member.id
        )