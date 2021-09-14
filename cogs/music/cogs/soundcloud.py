# RT.cogs.music.cogs - SoundCloud ... SouncCloudの音楽のAudioSourceなどを取得するためのモジュールです。

from copy import copy
import discord
import asyncio

from .youtube import (
    FLAT_OPTIONS, _make_get_source, _get,
    MusicData, MusicRawData, UploaderData
)


SC_OPTIONS = copy(FLAT_OPTIONS)
SC_OPTIONS["noplaylist"] = True


def _make_music_raw_data(data: dict) -> MusicRawData:
    return MusicRawData(
        url=data["url"], title=data["title"], thumbnail=data["thumbnail"],
        duration=data["duration"], uploader=UploaderData(
            name=data["uploader"], url=data["uploader_url"]
        ), get_source=_make_get_source(data["url"], SC_OPTIONS)
    )


async def get_music(
    url: str, author: discord.Member,
    loop: asyncio.AbstractEventLoop
) -> MusicData:
    return MusicData(
        _make_music_raw_data(await _get(url, FLAT_OPTIONS)), author
    )
