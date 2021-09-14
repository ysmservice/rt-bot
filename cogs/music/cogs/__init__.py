# RT.music - cogs

from typing import Union, Optional, List

import discord
import asyncio

from . import youtube, niconico, soundcloud
from .music import MusicData


async def get_music(
    url: str, author: discord.Member,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    search_max_result: int = 10, **kwargs
) -> Union[MusicData, List[MusicData]]:
    # 渡されたURLの音楽のデータを取り出します。プレイリストか検索の場合はリストとなります。
    loop = loop or asyncio.get_event_loop()

    if "nicovideo.jp" in url or "nico.ms" in url:
        return await niconico.get_music(url, author, loop, **kwargs)
    elif "www.youtube.com" in url or "youtu.be" in url:
        if "list" in url:
            return await youtube.get_playlist(url, author, loop, **kwargs)
        else:
            return await youtube.get_music(url, author, loop, **kwargs)
    elif "soundcloud.com" in url:
        return await soundcloud.get_music(url, author, loop)
    else:
        return await youtube.get_playlist(
            f"ytsearch{search_max_result}:{url}", author, loop, **kwargs
        )
