# RT TTS - Voiceroid

from aiofiles import open as async_open
from aiohttp import ClientSession
import asyncio


HEADERS = {
    'authority': 'cloud.ai-j.jp',
    'accept': 'text/javascript, application/javascript, */*; q=0.01',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 Edg/89.0.774.57',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.ai-j.jp',
    'sec-fetch-site': 'same-site',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://www.ai-j.jp/',
    'accept-language': 'ja,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
}

VOICEROIDS = {
    "iori": {
        "name": "伊織 弓鶴",
        "id": 1214,
        "zisa": 4
    },
    "tsuina": {
        "name": "ついなちゃん",
        "id": 1212,
        "zisa": 2.01
    },
    "itako": {
        "name": "東北 イタコ",
        "id": 1211,
        "zisa": 3.6
    },
    "sora": {
        "name": "桜乃 そら",
        "id": 1210,
        "zisa": 4
    },
    "kiritan": {
        "name": "東北きりたん",
        "id": 1209,
        "zisa": 3.3
    },
    "seika": {
        "name": "京町 セイカ",
        "id": 1208,
        "zisa": 2
    },
    "kou": {
        "name": "水奈瀬 コウ",
        "id": 1207,
        "zisa": 1.8
    },
    "shota": {
        "name": "月読 ショウタ",
        "id": 1204,
        "zisa": 3.8
    },
    "ai": {
        "name": "月読 アイ",
        "id": 1203,
        "zisa": 5.15
    },
    "zunko": {
        "name": "東北 ずん子",
        "id": 1202,
        "zisa": 3.85
    },
    "taka": {
        "name": "鷹の爪 吉田くん",
        "id": 1201,
        "zisa": 3.34
    },
    "una": {
        "name": "音街 ウナ",
        "id": 2006,
        "zisa": 3.65
    },
    "akari": {
        "name": "紲星 あかり",
        "id": 554,
        "zisa": 2.04
    },
    "yukari": {
        "name": "結月 ゆかり",
        "id": 553,
        "zisa": 4
    },
    "akane": {
        "name": "琴葉 茜",
        "id": 552,
        "zisa": 3.8
    },
    "aoi": {
        "name": "琴葉 葵",
        "id": 551,
        "zisa": 3.9
    }
}


async def get_url(
        session: ClientSession, name: str, text: str, ext: str = "ogg",
        vol: float = 1.0, speed: float = 1.0, pitch: float = 1.0
    ) -> str:
    """Voiceroidのデモ音源のダウンロードリンクを作ります。

    Parameters
    ----------
    session : aiohttp.ClientSession
        通信に使うセッションです。
    name : str
        Voiceroid名です。
    text : str
        読み上げる文字列です。
    ext : str, default "ogg"
        音源のファイルフォーマットの種類です。
    vol : float, default 1.0
        音量です。です。
    speed : float, default 1.0
        読み上げスピードです。
    pitch : float, default 1.0
        ピッチです。"""
    data = f"speaker_id={VOICEROIDS[name]['id']}&text={text}&ext={ext}&volume={vol}&speed={speed}&pitch={pitch}&range=1.0&callback=callback"

    async with session.post('https://cloud.ai-j.jp/demo/aitalk2webapi_nop.php',
                            headers=HEADERS,
                            data=data.encode("utf-8")) as res:
        url = f"https://cloud.ai-j.jp/demo/tmp/{(await res.text())[47:-3]}"
    return url


async def synthe(
        session: ClientSession, filename: str, name: str, text: str,
        ext: str = "ogg", vol: float = 1.0, speed: float = 1.0,
        pitch: float = 1.0, chunk_size: int = 1024
    ) -> None:
    """VOICEROIDのデモ音源を生成してもらいダウンロードします。

    Parameters
    ----------
    session : aiohttp.ClientSession
        通信に使うセッションです。
    filename : str
       ダウンロードするファイルの名前です。
    name : str
        VOICEROID名です。
    text : str
        読み上げる文字列です。
    ext : str, default "ogg"
        ダウンロードするファイルのフォーマットの種類です。
    vol : float, default 1.0
        音量です。
    speed : float, default 1.0
        読み上げスピードです。
    pitch : float, default 1.0
        ピッチです。
    chunk_size : int, default 1024
        いくつのチャンクに分けてダウンロードするかです。"""
    url = await get_url(session, name, text, ext, vol, speed, pitch)

    async with session.get(url) as res:
        async with async_open(filename, "wb") as f:
            await f.write(b"")

        async with async_open(filename, "ab") as f:
            async for chunk in res.content.iter_chunked(chunk_size):
                if chunk:
                    await f.write(chunk)


async def session_wraped_synthe(*args, **kwargs) -> None:
    """Syntheを自動でセッションを作り実行します。"""
    async with ClientSession() as session:
        await synthe(session, *args, **kwargs)


if __name__ == "__main__":
    name = input("voice >")
    text = input("text >")
    filename = input("file >")
    asyncio.run(
        session_wraped_synthe(
            filename, name, text, filename[filename.rfind("."):]
        )
    )