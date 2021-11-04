# RT.Utils - Typed

from types import SimpleNamespace

from sanic import Sanic, response
from discord.ext import commands
from jinja2 import Environment
from aiomysql import Pool


class TypedContext(SimpleNamespace):
    pool: Pool
    bot: "TypedBot"
    env: Environment

    def template(
        self, path: str, keys: dict, **kwargs
    ) -> response.BaseHTTPResponse:
        ...


class TypedSanic(Sanic):
    ctx: TypedContext


class TypedBot(commands.Bot):
    app: TypedSanic
    pool: Pool