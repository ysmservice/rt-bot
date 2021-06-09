# RT - Utils

from random import randint
from time import time


# Session ID Maker
def make_session_id(n: int = 5) -> str:
    base = str(time())
    for _ in range(n):
        base += str(randint(0, 9))
    return base


def get(objects, **kwargs):
    # discord.utils.getのRT製フレームワーク対応版みたいな。
    for object in objects:
        for key in kwargs:
            if object[key] == kwargs[key]:
                return object
    return None


def cc_int(object):
    # 変換できるなら整数に変換するやつ。
    try:
        return int(object)
    except ValueError:
        return None
    finally:
        return None


def has_roles(member, roles):
    return any(bool(get(
        member["roles"], id=role["id"])) for role in roles)


def roles2obj(guild, arg):
    roles_raw, roles = arg.split(','), []
    for role in roles_raw:
        if '@' in role:
            roles.append(get(guild["roles"], id=int(role[3:-1])))
        elif cc_int(role):
            roles.append(get(guild["roles"], id=int(role)))
        else:
            roles.append(get(guild["roles"], name=role))
    return roles


# Custom Converterの役職複数バージョン。
def Roles(data, ctx, arg):
    return roles2obj(data["guild"], arg)
    
