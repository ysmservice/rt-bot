# RT.music.cogs - YouTube

from youtube_dl import YoutubeDL


ytdl = YoutubeDL(
    {
        "format": "bestaudio/best",
        "default_search": "auto",
        "source_address": "0.0.0.0"
    }
)


class YouTubeMusic():
    pass
