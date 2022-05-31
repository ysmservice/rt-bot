# Free RT Utils - Checks

import discord


def isintable(x: str) -> bool:
    "渡された文字列が整数に変換可能かを調べます。"
    try:
        int(x)
    except ValueError:
        return False
    else:
        return True


def has_any_roles(member: discord.Member, roles: list[discord.Role]) -> bool:
    "ユーザーが指定されたロールのうちどれか1つでも持っているかを調べます。"
    return any(role in member.roles for role in roles)


def has_all_roles(member: discord.Member, roles: list[discord.Role]) -> bool:
    "ユーザーが指定されたロールをすべて持っているかを調べます。"
    return all(role in member.roles for role in roles)


def similer(before: str, after: str, check_length: int) -> bool:
    "beforeがafterとcheck_lengthの文字数分似ているかどうかを調べます。"
    return any(after[i:i + check_length] in before
               for i in range(len(after) - check_length))


def alpha2num(alpha: str):
    "アルファベットを数字に変換するやーつ(A->1, B->2といった具合に)"
    num = 0
    for index, item in enumerate(list(alpha)):
        num += pow(26, len(alpha) - index - 1) * (ord(item) - ord('A') + 1)
    return num


def num2alpha(num: int):
    "数字をアルファベットに変換するやーつ(1->A, 2->Bといった具合に)"
    if num <= 26:
        return chr(64 + num)
    elif num % 26 == 0:
        return num2alpha(num // 26 - 1) + chr(90)
    else:
        return num2alpha(num // 26) + chr(64 + num % 26)
