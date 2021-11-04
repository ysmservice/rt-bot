# RT.Utils - Typed

from types import SimpleNamespace

from discord.ext import commands
from aiomysql import Pool
from sanic import Sanic


class TypedContext(SimpleNamespace):
    pool: Pool
    bot: "TypedBot"


class TypedSanic(Sanic):
    ctx: TypedContext


class TypedBot(commands.Bot):
    app: TypedSanic
    pool: Pool