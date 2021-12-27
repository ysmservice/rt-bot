# RT AutoMod - Data Manager

from typing import (
    TYPE_CHECKING, TypeVar, NewType, TypedDict, Literal,
    Union, Optional, Dict, Tuple, List
)

from discord.ext import commands, tasks
import discord

from ujson import loads, dumps
from aiomysql import Cursor

from functools import wraps
from time import time

from rtutil import DatabaseManager

from .cache import Cache

if TYPE_CHECKING:
    from .__init__ import AutoMod


Warn = NewType("Warn", float)
class GuildData(TypedDict, total=False):
    ban: Warn
    mute: Warn
    invites: NewType("Invites", List[int])
    bolt: float
    invite_deleter: NewType("InviteDeleter", List[str])
    emoji: int


class HashableGuild(dict):

    guild_id: int = 0
    require_save: bool = False

    def __init__(self, guild_id: int, *args, **kwargs):
        self.guild_id = guild_id
        super().__init__(*args, **kwargs)

    def __hash__(self):
        return self.guild_id

    def __setitem__(self, key, value):
        self.require_save = True
        return super().__setitem__(key, value)


UserData = Dict[int, Cache]
SaveData = Tuple[Union[GuildData, HashableGuild], UserData]
Guild = Union[int, discord.Guild]


class DataManager(DatabaseManager):
    "セーブデータ管理用クラス"

    TABLES = ("AutoModData",)
    DEFAULTS = {
        "ban": 10, "mute": 8, "bolt": 60, "emoji": 15
    }

    def __init__(self, cog: "AutoMod"):
        self.cog, self.pool = cog, cog.bot.mysql.pool
        self._update_database.start()
        self.cog.bot.loop.create_task(self._prepare_table())

    async def _prepare_table(self, cursor: Cursor = None):
        await cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {self.TABLES[0]} (
                GuildID BIGINT PRIMARY KEY NOT NULL, GuildData JSON, UserData JSON
            );"""
        )

    @tasks.loop(minutes=10)
    async def _update_database(self):
        # 古いキャッシュの削除とセーブをするループです。
        now = time()
        for guild_id in list(self.cog.caches.keys()):
            if self.cog.caches[guild_id][0].require_save:
                # もしGuildDataがセーブを必要としているならセーブする。
                self.cog.bot.loop.create_task(
                    self.save_guild_data(guild_id, self.cog.caches[guild_id][0])
                )
                self.cog.caches[guild_id][0].reqiure_save = False
            for member_id in list(self.cog.caches[guild_id][1].keys()):
                if self.cog.caches[guild_id][1][member_id].require_save:
                    # UserDataがセーブを必要としているならセーブをする。
                    self.cog.bot.loop.create_task(
                        self.save_user_data(self.cog.caches[guild_id][1][member_id])
                    )
                    self.cog.caches[guild_id][1][member_id].require_save = False
                if self.cog.caches[guild_id][1][member_id].timeout <= now:
                    # もしタイムアウト(放置されている)キャッシュがあるなら消す。
                    del self.cog.caches[guild_id][1][member_id]
                if not self.cog.caches[guild_id][1]:
                    # もしサーバーのキャッシュが空になったらそれもいらないので消す。
                    del self.cog.caches[guild_id]

    def close(self):
        "コグアンロード時に呼び出されるべき関数です。"
        self._update_database.cancel()

    async def _read(self, cursor: Cursor, guild: Union[int, discord.Guild]) -> SaveData:
        # セーブデータを読み込む関数です。
        await cursor.execute(
            f"SELECT GuildData, UserData FROM {self.TABLES[0]} WHERE GuildID = %s;",
            getattr(guild, "id", guild)
        )
        if (row := list(map(loads, await cursor.fetchone()))):
            if isinstance(guild, int):
                guild = self.cog.bot.get_guild(guild)
            return HashableGuild(guild.id, row[0]), {
                key: Cache(self.cog, guild.get_member(key)) for key in row[1]
            }
        else:
            return HashableGuild(guild.id, {}), {}

    async def read(self, guild: Guild, cursor: Cursor = None) -> Optional[SaveData]:
        "セーブデータを読み込みます。"
        return await self._read(cursor, guild)

    def dump_user_data(self, data: Cache) -> str:
        "UserDataをdumpsします。"
        return dumps(data.items())

    def dump_user_datas(self, datas: Dict[int, Cache]) -> str:
        "UserDataの集まりをdumpsします。"
        return dumps({key: self.dump_user_data(value) for key, value in datas.items()})

    def _get_save_data_query(self, mode: Literal["Guild", "User"]) -> str:
        return f"""INSERT INTO {self.TABLES[0]} VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE {mode} = %s;"""

    async def save_user_data(self, data: Cache, cursor: Cursor = None) -> None:
        "UserDataをセーブします。"
        guild_data, currents = await self._read(cursor, data.guild)
        currents[data.member.id].update(data)
        await cursor.execute(
            self._get_save_data_query("User"),
            (
                data.guild.id, dumps(guild_data), (
                    currents := self.dump_user_datas(currents)
                ), currents
            )
        )

    async def save_guild_data(
        self, guild: Guild, data: GuildData, cursor: Cursor = None
    ) -> None:
        "GuildDataをセーブします。"
        current, currents = await self._read(cursor, guild)
        current.update(data)
        await cursor.execute(
            self._get_save_data_query("Guild"),
            (
                getattr(guild, "id", guild), dumps(current), (
                    currents := self.dump_user_datas(currents)
                ), currents
            )
        )


ReCaT = TypeVar("ReCaT")
def require_cache(function: ReCaT) -> ReCaT:
    "キャッシュがないと困るコマンドにつけるデコレータです。"
    @wraps(function)
    async def new(self: "AutoMod", ctx: commands.Context, *args, **kwargs):
        if ctx.guild.id not in self.caches:
            self.caches[ctx.guild.id] = await self.read(ctx.guild)
        if hasattr(ctx, "member"):
            if ctx.member.id not in self.caches[ctx.guild.id][1]:
                _, currents = await self.read(ctx.guild)
                self.caches[ctx.guild.id][1][ctx.member.id] = currents.get(
                    ctx.member.id, Cache(self, ctx.member, {})
                )
        return await function(self, ctx, *args, **kwargs)
    return new