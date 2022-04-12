# RT - Lib

from typing import Union

from discord.ext import commands # type: ignore
import discord

from pymysql.err import OperationalError

from .slash import Context as SlashContext
from . import mysql_manager as mysql
from .data_manager import Table
from .ext import componesy
from .typed import RT, sendableString
from .cacher import CacherPool, Cacher, Cache

# 非推奨だが一応使えるようにimportしておく。
from rtutil.oldrtlib import webhook_send, tasks_extend, send_kwargs
from rtutil.oldrtlib import lib_setup as setup


DatabaseManager = mysql.DatabaseManager
Context = Union[SlashContext, commands.Context]


# webhook_sendを新しく定義する。
discord.abc.Messageable.webhook_send = webhook_send # type: ignore
discord.ext.easy = componesy # type: ignore

# discord.ext.tasksのタスクがデータベースの操作失敗によって止まることがないようにする。
tasks_extend()
