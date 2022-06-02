# Free RT Util - Sec URL

from typing import TypedDict

from aiohttp import ClientSession
from ujson import loads

from data.headers import SECURL_HEADERS as HEADERS


class SecURLData(TypedDict, total=False):
    "SecURLのURLチェックの結果のデータの型です。"
    status: int
    imgWidth: int
    imgHeight: int
    reqURL: str
    resURL: str
    title: str
    anchors: list
    viruses: list
    blackList: list
    annoyUrl: str
    img: str
    capturedDate: str


async def check(
    session: ClientSession, url: str, wait_time: int = 1,
    browser_width: int = 965, browser_height: int = 683,
    headers: dict = HEADERS
) -> SecURLData:
    """渡されたURLをSecURLでチェックします。
    Parameters
    ----------
    session : aiohttp.ClientSession
        通信に使うsessionです。
    url : str
        チェックするURLです。
    wait_time : int, default 1
        どれだけ待つかです。
    browser_width : int, default 965
        ブラウザのサイズです。
    browser_height : int, default 683
        ブラウザのサイズです。
    headers : dict, default HEADERS
        通信に使うヘッダーです。通常は変更しなくても大丈夫です。
    Raises
    ------
    ValueError : URLにアクセスできなかった際などの失敗時に発生します。"""
    async with session.post(
        "https://securl.nu/jx/get_page_jx.php", data={
            "url": url, 'waitTime': str(wait_time),
            'browserWidth': str(browser_width),
            'browserHeight': str(browser_height), 'from': ''
        }, headers=headers
    ) as r:
        return loads(await r.text())


def get_capture(
    data: SecURLData, full: bool = False
) -> str:
    """渡されたデータにある`img`のデータからURLを作ります。
    Parameters
    ----------
    data : SecURLData
        SecURLから返された辞書データです。
    full : bool
        上から一番下までの写真のURLを返すかどうかです。"""
    return (
        f"https://securl.nu/save_local_captured.php?key={data['img'][10:-4]}"
        if full else f"{HEADERS['Origin']}{data['img']}"
    )
