# RT.music.cogs - Type

from typing import TypedDict, Optional, Type, Callable, Tuple

import discord


class UploaderData(TypedDict):
    name: str
    url: Optional[str]


GetSource = Callable[[], Tuple[Type[discord.FFmpegPCMAudio], Callable[[], None]]]


class MusicRawDataForJson(TypedDict):
    url: str
    title: str
    thumbnail: str
    duration: int
    uploader: UploaderData


class MusicRawData(MusicRawDataForJson):
    get_source: GetSource
