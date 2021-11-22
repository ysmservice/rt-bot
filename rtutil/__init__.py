# rtutil

from typing import List

import discord

from .minesweeper import Ms as Minesweeper
from .data_manager import DatabaseManager


def check_int(v: str) -> bool:
    # 渡された文字列が整数かどうかをチェックします。
    try:
        int(v)
    except BaseException:
        return False
    else:
        return True


def similer(before: str, after: str, check_length: int) -> bool:
    # beforeがafterとcheck_lengthの文字数分似ているかどうかをチェックします。
    return any(after[i:i + check_length] in before
               for i in range(len(after) - check_length))


def has_roles(member: discord.Member, roles: List[discord.Role]) -> bool:
    # メンバーが指定された役職の中にあるかどうかを確かめます。
    return any(role in member.roles for role in roles)


def role2obj(guild: discord.Guild, arg: str) -> List[discord.Role]:
    # `役職1, 役職2, ...`のようになってるものをロールオブジェクトに変換します。
    roles_raw, roles = arg.split(','), []
    for role in roles_raw:
        if '@' in role:
            roles.append(guild.get_role(int(role[3:-1])))
        elif check_int(role):
            roles.append(guild.get_role(int(role)))
        else:
            roles.append(discord.utils.get(guild.roles, name=role))
    return roles


class Roler(discord.ext.commands.Converter):
    # discord.pyのコマンドフレームワークのコンバーターで複数の役職をロールオブジェクトに交換します。
    async def convert(self, ctx, arg):
        return role2obj(ctx.guild, arg)


async def get_webhook(
    channel: discord.TextChannel, name: str = "RT-Tool"
) -> discord.Webhook:
    "ウェブフックを取得します。"
    return discord.utils.get(await channel.webhooks(), name=name)