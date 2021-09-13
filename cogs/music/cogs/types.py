# RT.music.cogs - Type

from typing import TypedDIct, Type, Callable

import discord


class uploaderData(TypedDict):
    name: str
    url: str


GetSource = Callable[[str], discord.FFmpegPCMAudio]


class MusicRawData(TypedDict):
    url: str
    title: str
    description: str
    thumbnail: str
    duration: int
    uploader: UploaderData
    get_source: GetSource
