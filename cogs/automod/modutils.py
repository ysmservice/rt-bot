# RT.AutoMod - Mod Utils

from typing import Optional, Union, Dict

from discord.ext import commands

from emoji import UNICODE_EMOJI
from functools import wraps
from re import findall


def similer(before: str, after: str, check_characters: Optional[int] = None) -> bool:
    # 渡されたbeforeとafterが似てるかチェックします。
    if sum(map(after.count, ("@", "<", ">"))) // 3 > 2:
        # 二個メンションがあれば問答無用でTrueを返す。
        return True

    after_length = len(after)
    if check_characters is None:
        check_characters = after_length // 4
    if after_length < check_characters or check_characters < 5:
        check_characters = after_length
    return any(
        after[i:i + check_characters] in before
        for i in range(after_length - check_characters)
    )


def check(func):
    # AutoMod設定コマンドを実行する権限を持っているか確認をするデコレータです。
    return commands.has_permissions(
        ban_members=True, manage_roles=True
    )(func)


def emoji_count(text: str) -> int:
    # 渡された文字列にある絵文字の数を数えます。
    return len(findall("<a?:.+:\d+>", text)) \
        + len([char for char in text if char in UNICODE_EMOJI])


def assertion_error_handler(description: Union[str, Dict[str, str]]):
    # AssertionErrorが発生したら渡された文字列を返信するようにするデコレータです。
    def decorator(coro):
        @wraps(coro)
        async def new(self, ctx, *args, **kwargs):
            try:
                return await coro(self, ctx, *args, **kwargs)
            except AssertionError:
                await ctx.reply(description)
        return new
    return decorator