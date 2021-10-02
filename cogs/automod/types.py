# RT.AutoMod - Types

from typing import TypedDict, Tuple, Dict, List


class Data(TypedDict, total=False):
    warn: Dict[int, int]
    emoji: int
    invite_filter: bool
    invites: List[int]
    level: int
    mute: Tuple[int, int]
    ban: int