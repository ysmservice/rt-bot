# free RT utils - checks

from typing import Union

from discord.ext import commands
import discord


def isintable(x: str) -> bool:
    "渡された文字列が整数に変換可能かを調べます。"
    try:
        int(x)
    except:
        return False
    else:
        return True


def has_any_roles(member: discord.Member, roles: list[discord.Role]) -> bool:
    "ユーザーが指定されたロールのうちどれか1つでも持っているかを調べます。"
    return any(role in member.roles for role in roles)


def has_all_roles(member: discord.Member, roles: list[discord.Role]) -> bool:
    "ユーザーが指定されたロールをすべて持っているかを調べます。"
    return all(role in member.roles for role in roles)
