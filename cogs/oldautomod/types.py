# RT.AutoMod - Types

from typing import TypedDict, Tuple, Dict, List


class Data(TypedDict, total=False):
    # AutoModのデータの辞書の型のクラスです。
    warn: Dict[int, float]
    emoji: int
    invite_filter: bool
    invites: List[int]
    ignores: List[int]
    level: int
    mute: Tuple[int, int]
    ban: int
    withdrawal: int
    invite_remover: bool
    ignore_invite_remover: List[int]


class SpamCacheData(TypedDict, total=False):
    # スパムを検知するためにメッセージ送信毎に保存するキャッシュの辞書の型のクラスです。
    before: str
    time: float
    count: int


class Caches(TypedDict):
    withdrawal: List[Tuple[int, int]]