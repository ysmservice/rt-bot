# RT.cogs.music - Util

import discord


def check_dj(member: discord.Member) -> bool:
    # 渡されたメンバーが場合によってはDJが必要なコマンドのためのDJチェックをする関数です。
    return (
        len([m for m in member.voice.channel.members if not m.bot]) == 1
        or discord.utils.get(member.roles, name="DJ")
    )
