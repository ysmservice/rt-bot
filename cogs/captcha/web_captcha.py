# RT - Captcha Web Manager

import discord

from typing import Dict, Tuple
from time import time
import reprypt
import ujson


class WebCaptcha:
    def __init__(self, captcha_cog, secret: str):
        self.cog = captcha_cog
        self.secret: str = secret
        self.queue: Dict[str, Tuple[int, float]] = {}
        self.base_url = (
            "http://localhost:5500/"
            if self.cog.bot.test
            else "https://rt-bot.com/"
        )
        try:
            self.cog.bot.web.add_route(
                self.endpoint, "/api/captcha/<userdata>",
                methods=["GET", "POST"]
            )
        except Exception as e:
            print("Ignored error on WebCaptcha:", e)

    def encrypt(self, data: dict) -> str:
        return reprypt.encrypt(
            ujson.dumps(data), self.secret,
            converter=reprypt.convert_hex
        )

    def decrypt(self, data: str) -> dict:
        return ujson.loads(reprypt.decrypt(
            data, self.secret,
            converter=reprypt.convert_hex
        ))

    async def endpoint(self, request, userdata):
        # hCaptchaの認証のエンドポイントです。
        # URLにあるユーザー特定用の暗号化されたユーザーデータを読み込む。
        userdata = self.decrypt(userdata)
        key = f"{userdata['guild_id']}-{userdata['user_id']}"
        if key in self.queue:
            # hCaptchaの認証結果を取得する。
            data = {"secret": self.secret,
                    "response": request.form.get("h-captcha-response")}
            async with self.cog.bot.session.post(
                    "https://hcaptcha.com/siteverify",
                    data=data) as r:
                data = await r.json(loads=ujson.loads)

            if data["success"]:
                # もしhCaptchaの認証が成功しているなら。
                if ((guild := self.cog.bot.get_guild(userdata["guild_id"]))
                    and (member := guild.get_member(userdata["user_id"]))):
                    # 役職などを取得して役職を付与する。
                    row = await self.cog.load(userdata["guild_id"])
                    role = guild.get_role(row[3])
                    if role:
                        try:
                            await member.add_roles(role)
                        except Exception as e:
                            result = ("認証に失敗しました。"
                                "付与する役職がRTの役職より下にあるか確認してください。\n"
                                "Failed, make sure that the role position below the RT role position.")
                        else:
                            result = ("認証に成功しました。"
                                      "役職が付与されました。\n"
                                      "Success!")
                            del self.queue[key]
                    else:
                        result = ("うぅ、、役職が見つからなかったから認証できなかったのです。"
                                  "すみません！！\n"
                                  "Ah, I couldn't find the role to add to you.")
            else:
                result = ("認証に失敗しました。"
                    "あなたがロボットではないことの確認ができなかったです。\n"
                    "Failed, I couldn't make sure you were not Robot. I'm sorry!")
        else:
            result = (
                "あなたが誰なのかわからないので"
                "認証に失敗しました。"
                "Discordに戻ってもう一度URLを開いてください。\n"
                "Failed, Who are you? Please back to discord and open captcha link again."
            )

        return await self.cog.bot.web_manager.template(
            "captcha_result.html", result=result
        )

    async def captcha(self, channel: discord.TextChannel,
                      member: discord.Member) -> None:
        self.queue[f"{member.guild.id}-{member.id}"] = (member.id, time())
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