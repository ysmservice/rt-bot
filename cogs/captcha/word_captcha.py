# RT - Captcha Word Manager

from typing import Dict, Tuple
from .__init__ import Captcha

from discord.ext import commands
import discord


class WordCaptcha(commands.Cog):
    def __init__(self, captcha_cog: Captcha):
        self.cog: Captcha = captcha_cog
        self.queue: Dict[str, Tuple[int, str]] = {}
        self.cog.bot.add_litener(self.on_message, "on_message")

    async def captcha(self, channel: discord.TextChannel,
                      member: discord.Member) -> None:
        await channel.send(
            {"ja": f"{member.mention}, 合言葉を入力してください。",
             "en": f"{member.mention}, ..."},
            target=member.id
        )
        row = await self.cog.load(channel.guild.id)
        self.queue[f"{channel.id}-{member.id}"] = (row[3], row[4])

    async def on_message(self, message: discord.Message) -> None:
        if (row := self.queue.get(
                f"{message.channel.id}-{message.author.id}")):
            if message.content == row[1]:
                role = message.guild.get_role(row[0])
                if role:
                    try:
                        await message.author.add_roles(role)
                    except Exception as e:
                        await message.reply(
                            {"ja": ("認証に失敗しました。\n"
                                    "付与する役職がRTの役職より下にあるか確認してください。\n"
                                    f"エラーコード：{e}"),
                             "en": "..."},
                        )
                    else:
                        await message.reply(
                            {"ja": "認証に成功しました。",
                            "en": "..."}
                        )
                else:
                    await message.reply(
                        {"ja": "役職が見つからないため認証に失敗しました。",
                         "en": "..."}
                    )
            else:
                await message.reply(
                    {"ja": "合言葉が違います。",
                     "en": "..."}
                )