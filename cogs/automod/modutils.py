# RT AUtoMod - Mod Utils

import discord

from time import time

from .cache import Cache


def similar(before: str, after: str, check_characters: int = 30):
    "文章が似ているかチェックします。"
    return any(
        after[i:i + check_characters] in before for i in range(check_characters)
    )


def join(message: discord.Message) -> str:
    "渡されたメッセージにある文字列を全て合体させます。"
    content = message.content or ""
    for embed in message.embeds:
        content += "".join(map(lambda x: getattr(embed, x), ("title", "description"))) \
            + embed.footer.text
    for attachment in message.attachments:
        content += attachment.filename
    return content


def is_spam(self: Cache, message: discord.Message) -> bool:
    "スパムかどうかをチェックします。"
    if self.update_cache(message) is None:
        return False
    if self.checked <= time() + 0.5:
        return True
    return similar(self.before_content, join(message))