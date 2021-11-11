# RT - Captcha Image Manager

from jishaku.functools import executor_function
from captcha.image import ImageCaptcha
from typing import Optional, Dict, Tuple
from aiofiles.os import remove
from random import randint
from os import listdir
from time import time

import discord


class ImageCaptcha(ImageCaptcha):

    PASSWORD_LENGTH = 5

    def __init__(
        self, captcha_cog,
        font_path: str = "data/captcha/SourceHanSans-Normal.otf"
    ):
        self.cog = captcha_cog
        super().__init__(fonts=[font_path])
        self.queue: Dict[str, Tuple[str, float]] = {}
        self.cog.bot.add_listener(self.on_message, "on_message")
        self.cog.bot.add_listener(self.on_close, "on_close")

    @executor_function
    def create_image(
        self, path: str, characters: Optional[str] = None
    ) -> str:
        characters = "".join(
            str(randint(0, 9))
            for _ in range(self.PASSWORD_LENGTH)
        ) if characters is None else characters
        self.write(characters, path)
        return characters

    async def captcha(self, channel: discord.TextChannel,
                      member: discord.Member) -> None:
        name = f"{channel.id}-{member.id}"
        path = f"data/captcha/{name}.png"
        self.queue[name] = (await self.create_image(path), time())
        await channel.send(
            {"ja": f"{member.mention}, 画像にある数字を入力してください。" \
                "\n一時間放置されると無効になるので一時間放置した場合はサーバーに参加し直してください。",
             "en": f"{member.mention}, Please, type number on the picture." \
                 "\nIf you leave it for an hour, it will become invalid, so if you leave it for an hour, please rejoin the server."},
            target=member.id, file=discord.File(path)
        )
        await remove(path)

    async def on_message(self, message: discord.Message) -> None:
        name = f"{message.channel.id}-{message.author.id}"
        if name in self.queue and len(message.content) == self.PASSWORD_LENGTH:
            if message.content == self.queue[name][0]:
                row = await self.cog.load(message.guild.id)
                role = message.guild.get_role(row[3])

                if role:
                    try:
                        await message.author.add_roles(role)
                    except Exception as e:
                        await message.channel.send(
                            {"ja": (f"{message.author.mention}, 役職を付与することができませんでした。\n"
                                    "付与する役職の位置がRTより下にあるか確認してください。\n"
                                    f"エラーコード：`{e}`"),
                             "en": f"{message.author.mention}, Failed, make sure that the role position below the RT role position."}
                        )
                    else:
                        await message.channel.send(
                            {"ja": f"{message.author.mention}, 認証に成功しました。",
                             "en": f"{message.author.mention}, Success!"}
                        )
                        self.cog.remove_cache(message.author)
                else:
                    await message.channel.send(
                        {"ja": f"{message.author.mention}, 設定されている役職が見つからないため認証に失敗しました。",
                         "en": f"{message.author.mention}, Failed, I couldn't find the role to add you."}
                    )
            else:
                await message.channel.send(
                    message.author.mention,
                    embed=discord.Embed(
                        description={
                            "ja": "認証に失敗しました。\nもしできているはずなのにできない際はこちらを確認してください。\nhttp://tasuren.syanari.com/RT/careful.png",
                            "en": "Failed, Please confirm your number is true.\nNote that 1 and 7 are similar, so please pay attention to that."
                        }, color=self.cog.bot.colors["normal"]
                    )
                )

    async def on_close(self, _):
        # Bot終了時にもし画像認証の画像が残っているのなら削除しておく。
        for name in listdir("data/captcha"):
            if name.endswith(".png"):
                await remove(f"data/captcha/{name}")
