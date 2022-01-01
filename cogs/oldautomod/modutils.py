# RT.AutoMod - Mod Utils

from typing import Optional, Union, Dict

from discord.ext import commands

from functools import wraps
from emoji import emoji_lis
from re import findall


def similer(before: str, after: str, check_characters: Optional[int] = None) -> bool:
    # 渡されたbeforeとafterが似てるかチェックします。
    if sum(map(after.count, ("@", "<", ">"))) // 3 > 2:
        # 二個メンションがあれば問答無用でTrueを返す。
        return True

    # もし「...」だけでスパムしているのなら元に戻す。
    if not after:
        after = tmp

    after_length = len(after)
    if check_characters is None:
        check_characters = after_length if after_length < 7 else 10
    return any(
        after[i:i + check_characters] in before
        for i in range(check_characters)
    )


def check(func):
    # AutoMod設定コマンドを実行する権限を持っているか確認をするデコレータです。
    return commands.has_permissions(
        ban_members=True, manage_roles=True
    )(func)


def emoji_count(text: str) -> int:
    # 渡された文字列にある絵文字の数を数えます。
    return len(findall("<a?:.+:\d+>", text)) \
        + len([char for char in text if emoji_lis(char)])


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