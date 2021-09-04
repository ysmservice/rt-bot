# RTLib - (C) 2021 RT-Team
# Author : tasuren

from discord.ext import commands
import discord

from typing import Union, Tuple, List
from functools import wraps
from copy import copy
import asyncio

from .web_manager import WebManager
from .backend import *
from . import mysql_manager as mysql
from .ext import componesy
from .oauth import OAuth



async def webhook_send(
        channel, *args, webhook_name: str = "RT-Tool", **kwargs):
    """`channel.send`感覚でウェブフック送信をするための関数です。  
    `channel.webhook_send`のように使えます。  
    
    Parameters
    ----------
    *args : tuple
        discord.pyのWebhook.sendに入れる引数です。
    webhook_name : str, defualt "RT-Tool"
        使用するウェブフックの名前です。  
        存在しない場合は作成されます。
    **kwargs : dict
        discord.pyのWebhook.sendに入れるキーワード引数です。"""
    if isinstance(channel, commands.Context):
        channel = channel.channel
    wb = (wb if (wb := discord.utils.get(
            await channel.webhooks(), name=webhook_name))
          else await channel.create_webhook(name=webhook_name))
    try:
        return await wb.send(*args, **kwargs)
    except discord.InvalidArgument as e:
        if webhook_name == "RT-Tool":
            return await webhook_send(channel, *args, webhook_name="R2-Tool", **kwargs)
        else:
            raise e


discord.abc.Messageable.webhook_send = webhook_send
discord.ext.easy = componesy


def setup(bot, only: Union[Tuple[str, ...], List[str]] = []):
    """rtlibにあるエクステンションを全てまたは指定されたものだけ読み込みます。

    Notes
    -----
    これを使えば正しい順番で読み込まれるため、通常はこれを使い一括でRTのエクステンションを読み込むべきです。

    Parameters
    ----------
    bot
        DiscordのBotです。
    only : Union[Tuple[str, ...], List[str]], optional
        読み込むエクステンションを限定します。  
        例：`("componesy", "embeds")`とすれば`componesy`と`embeds`のみを正しい順番で読み込みます。"""
    for name in ("embeds", "on_full_reaction", "dochelp", "debug"):
        if name in only or only == []:
            try:
                bot.load_extension("rtlib.ext." + name)
            except commands.errors.ExtensionAlreadyLoaded:
                pass
    bot.load_extension("rtlib.slash")


class DatabaseLocker:
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not hasattr(cls, "lock"):
            for name in dir(cls.__mro__[-3]):
                if not name.startswith("_"):
                    coro = getattr(cls, name)
                    if asyncio.iscoroutinefunction(coro):
                        setattr(cls, name, cls.wait_until_unlock(coro))
            cls.lock = None

    async def _close_cursor(self, auto_cursor):
        if auto_cursor:
            await self.cursor.close()
        # 違うやつが操作できるようにする。
        self.lock.set()

    @staticmethod
    def wait_until_unlock(coro):
        @wraps(coro)
        async def new_coro(self, *args, **kwargs):
            if self.lock is None:
                self.lock = asyncio.Event(
                    loop=getattr(getattr(self, "db", None), "loop", None)
                )
                self.lock.set()
            # 他のデータベース操作が終わるまで待つ。
            await self.lock.wait()
            # 今度はこっちがデータベースを操作する番ということで他が捜査できないようにする。
            self.lock.clear()
            # もし自動でcursorを取得するように言われたならそうする。
            if (auto_cursor := getattr(self, "auto_cursor", False)):
                self.cursor = self.db.get_cursor()
                await self.cursor.prepare_cursor()
            # エラーが起きた際にカーソルを閉じれないということを防ぐためにエラーを一度回収する。
            try:
                data = await asyncio.wait_for(
                    coro(self, *args, **kwargs), timeout=5
                )
            except Exception as e:
                await self._close_cursor(auto_cursor)
                raise e
            else:
                await self._close_cursor(auto_cursor)
            return data
        return new_coro


class DatabaseManager:
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for c in cls.__mro__:
            if (cls.__name__.startswith("Data")
                    and not c.__name__.startswith(
                        ("DatabaseL", "DatabaseM"))):
                for name in dir(c):
                    if not name.startswith("_"):
                        coro = getattr(cls, name)
                        if asyncio.iscoroutinefunction(coro):
                            setattr(cls, name, cls.prepare_cursor(coro))

    async def _close(self, conn, cursor):
        await cursor.close()
        conn.close()
        del cursor

    @staticmethod
    def prepare_cursor(coro):
        @wraps(coro)
        async def new_coro(self, *args, **kwargs):
            conn = await self.db.get_database()
            cursor = conn.get_cursor()
            await cursor.prepare_cursor()
            if self.bot.test:
                self.bot.print(
                    "[DEBUG]", f"[{coro.__name__}]",
                    "Database Control", args
                )
            try:
                data = await coro(self, cursor, *args, **kwargs)
            except Exception as e:
                await self._close(conn, cursor)
                raise e
            else:
                await self._close(conn, cursor)
                return data
            finally:
                self.bot.print(
                    "[DEBUG]", f"[{coro.__name__}]",
                    "Database Cursor Close",
                    "Connection Count:", self.db.pool.size,
                    "Connection Freesize:", self.db.pool.freesize
                )
        return new_coro