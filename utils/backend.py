# RT.Utils - Backend

from typing import Callable, Any, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask_misaka import Misaka
from sanic.response import html
from sanic.log import logger

from asyncio import AbstractEventLoop
from aiomysql import create_pool

from .typed import TypedSanic, TypedBot


def NewSanic(
    bot_args: tuple, bot_kwargs: dict, token: str, reconnect: bool,
    on_setup_bot: Callable[[TypedBot], Any], pool_args: tuple, pool_kwargs: dict,
    template_engine_exts: Sequence[str], template_folder: str,
    *sanic_args, **sanic_kwargs
) -> TypedSanic:
    app: TypedSanic = TypedSanic(*sanic_args, **sanic_kwargs)

    # テンプレートエンジンを用意する。
    app.ctx.env = Environment(
        loader=FileSystemLoader(template_folder),
        autoescape=select_autoescape(template_engine_exts),
        enable_async=True
    )
    app.ctx.env.filters.setdefault(
        "markdown", Misaka(autolink=True)
    )

    async def template(path, keys, **kwargs):
        return html(await app.ctx.env.get_template(path).render(**keys), **kwargs)
    app.ctx.template = template
    del template

    @app.listener("before_server_start")
    async def prepare(app: TypedSanic, loop: AbstractEventLoop):
        # データベースのプールの準備をする。
        pool_kwargs["loop"] = loop
        app.ctx.pool = await create_pool(*pool_args, **pool_kwargs)
        app.ctx.bot.pool = app.ctx.pool
        # Discordのデバッグ用ののBotの準備をする。
        bot_kwargs["loop"] = loop
        app.ctx.bot = TypedBot(*bot_args, **bot_kwargs)
        app.ctx.bot.app = app
        on_setup_bot(app.ctx.bot)
        await app.ctx.bot.start(token, reconnect=reconnect)
        logger.info("Connected to Discord")

    @app.listener("after_server_stop")
    async def close(app: TypedSanic, _: AbstractEventLoop):
        # プールとBotを閉じる。
        app.ctx.pool.close()
        app.ctx.bot.close()

    return app