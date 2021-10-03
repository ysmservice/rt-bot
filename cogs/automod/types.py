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


class CacheData(TypedDict):
    before: str
    time: float
    count: int