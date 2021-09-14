# RT.music.cogs - Type

from typing import TypedDict, Optional, Type, Callable, Tuple

import discord


class UploaderData(TypedDict):
    name: str
    url: Optional[str]


GetSource = Callable[[], Tuple[Type[discord.FFmpegPCMAudio], Callable[[], None]]]


class MusicRawData(TypedDict):
    url: str
    title: str
    thumbnail: str
    duration: int
    uploader: UploaderData
    get_source: GetSource
