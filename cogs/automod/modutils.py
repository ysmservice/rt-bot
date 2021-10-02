# RT.AutoMod - Mod Utils

from discord.ext import commands
import discord


def similer(before: str, after: str, check_characters: int = 5) -> bool:
    # 渡されたbeforeとafterが似てるかチェックします。
    if (after_length := len(after)) < check_characters:
        check_characters = after_length
    return any(
        after[i:i + check_characters] in before
        for i in range(after_length - check_characters)
    )


def check(func):
    return commands.has_permissions(
        ban_members=True, manage_roles=True
    )(func)