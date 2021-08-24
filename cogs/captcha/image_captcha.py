# RT - Captcha Image Manager

from jishaku.functools import executor_function
from captcha.image import ImageCaptcha
from aiofiles.os import remove
from typing import Type, Dict
from random import randint

from discord.ext import commands
import discord

from .__init__ import Captcha


class ImageCaptcha(ImageCaptcha):

    PASSWORD_LENGTH = 5

    def __init__(
            self, captcha_cog: Captcha,
            font_path: str = "data/captcha/SourceHanSans-Normal.otf"
            ):
        self.cog: Captcha = captcha_cog
        super().__init__(fonts=[font_path])
        self.queue: Dict[str, str] = {}
        self.cog.bot.add_litener(self.on_message, "on_message")

    @executor_function
    def create_image(
            self, path: str, characters: str = "".join(
                randint(0, 9)
                for _ in range(PASSWORD_LENGTH))
            ) -> str:
        self.write(characters, path)
        return characters

    async def captcha(self, channel: discord.TextChannel,
                      member: discord.Member) -> None:
        name = f"{channel.id}-{member.id}"
        path = f"/data/captcha/{name}.png"
        self.queue[name] = await self.create_image(path)
        await channel.send(
            {"ja": "画像にある数字を入力してください。",
             "en": "Please, type number on the picture."},
            target=member.id, file=discord.File(path)
        )
        await remove(path)

    async def on_message(self, message: discord.Message) -> None:
        name = f"{message.channel.id}-{message.author.id}"
        if name in self.queue and len(message.content) == self.PASSWORD_LENGTH:
            if message.content == self.queue[name]:
                await message.channel.typing()
                row = await self.cog.load(message.guild.id)
                role = message.guild.get_role(row[3])

                if role:
                    try:
                        await message.author.add_roles(role)
                    except Exception as e:
                        await message.reply(
                            {"ja": ("役職を付与することができませんでした。\n"
                                    "付与する役職の位置がRTより下にあるか確認してください。\n"
                                    f"エラーコード：`{e}`"),
                             "en": "..."}
                        )
                    else:
                        await message.reply(
                            {"ja": "認証に成功しました。",
                             "en": "..."}
                        )
                else:
                    await message.reply(
                        {"ja": "設定されている役職が見つからないため認証に失敗しました。",
                         "en": "..."}
                    )
            else:
                await message.reply(
                    {"ja": "認証に失敗しました。\n番号があっているか確認してください。",
                     "en": "..."}
                )
