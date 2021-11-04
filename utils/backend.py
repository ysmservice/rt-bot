# RT.Utils - Backend

from typing import Callable, Any

from asyncio import AbstractEventLoop
from aiomysql import create_pool
from sanic.log import logger

from .typed import TypedSanic, TypedBot


def NewSanic(
    bot_args: tuple, bot_kwargs: dict, token: str, reconnect: bool,
    on_setup_bot: Callable[[TypedBot], Any], pool_args: tuple, pool_kwargs: dict,
    *sanic_args, **sanic_kwargs
) -> TypedSanic:
    app: TypedSanic = TypedSanic(*sanic_args, **sanic_kwargs)


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
        on_setup_bot(bot)
        await app.ctx.bot.start(token, reconnect=reconnect)
        logger.info("Connected to Discord")


    @app.listener("after_server_stop")
    async def close(app: TypedSanic, _: AbstractEventLoop):
        # プールとBotを閉じる。
        app.ctx.pool.close()
        app.ctx.bot.close()


    return app