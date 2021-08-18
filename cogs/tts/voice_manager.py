# RT TTS - Voice Manager

from aiofiles import open as async_open
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from ujson import load, dumps
from typing import Optional
from alkana import get_kana
from pykakasi import kakasi
from re import findall, sub
from os import listdir

from . import aquestalk
from . import openjtalk
from . import voiceroid


# 辞書を読み込む。
with open("cogs/tts/dic/allow_characters.csv") as f:
    ALLOW_CHARACTERS = f.read().split()
with open("cogs/tts/dic/dictionary.json", "r") as f:
    dic = load(f)
# pykakasiの準備をする。
kks = kakasi()


class VoiceManager:
    """音声合成を簡単に行うためのクラスです。"""

    HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0'}
    REPLACE_CHARACTERS = {
        "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
        "ァ": "あ", "ィ": "い", "ゥ": "う", "ェ": "え", "ォ": "お"
    }

    def __init__(self, session: ClientSession, voices: dict):
        self.session: ClientSession = session
        self.voices: dict = voices

        aquestalk.load_libs(
            {
                name: voices[name]["path"]
                for name in voices
                if voices[name]["mode"] == "AquesTalk"
            }
        )

    async def synthe(self, voice: str, text: str, file_path: str,
                     dictionary: str = "/var/lib/mecab/dic/open-jtalk/naist-jdic",
                     speed: float = 1.0) -> Optional[None]:
        """音声合成をします。

        Parameters
        ----------
        voice : str
            誰に読ませるかです。
        text : str
            読み上げる文字列です。
        file_path : str
            ファイルのパスです。
        dictionary : str, default "/var/lib/mecab/dic/open-jtalk/naist-jdic"
            OpenJTalkの辞書のパスです。
        speed : float, default 1.0
            読み上げスピードです。"""
        data = self.voices[voice]
        # URLがあれば交換する。
        text = sub(
            "https?://[\\w/:%#\\$&\\?\\(\\)~\\.=\\+\\-]+",
            "ゆーあーるえる", text
        )
        # 文字列を最適な文字列にする。
        if len(text) > 40:
            text = text[:41] + " いかしょうりゃく"
        text = self.delete_disallow(
            self.convert_kanji(await self.text_parser(text))
        )
        # 音声合成をする。
        if text:
            if data["mode"] == "AquesTalk":
                await aquestalk.synthe(
                    voice, file_path, text, int(95 * (speed or 1.0))
                )
            elif data["mode"] == "OpenJTalk":
                await openjtalk.synthe(
                    data["path"], dictionary, file_path, text, speed=speed or 1.0
                )
            elif data["mode"] == "VOICEROID":
                return await voiceroid.get_url(
                    self.session, data["path"], text, speed=speed or 1.0
                )
        else:
            return "None"

    def delete_disallow(self, text: str) -> str:
        """文字列のひらがな以外を削除します。

        Parameters
        ----------
        text : str
            対象の文字列です。"""
        for char in self.REPLACE_CHARACTERS:
            text = text.replace(char, self.REPLACE_CHARACTERS[char])
        return "".join(char for char in text if char in ALLOW_CHARACTERS)

    def convert_kanji(self, text: str) -> str:
        """文字列にある漢字をひらがなに置き換えます。

        Parameters
        ----------
        text : str
            対象の文字列です。"""
        for item in kks.convert(text):
            text = text.replace(item["orig"], item["hira"])
        return text

    async def text_parser(self, text: str) -> str:
        """文字列にある英語をカタカナ読みにします。

        Parameters
        ----------
        text : str
            対象の文字列です。"""
        text = text.replace("\n", "、").lower()
        results = findall("[a-zA-Z]+", text)

        for result in results:
            # alkanaで英単語を交換する。
            after = get_kana(result)

            if not after:
                # もしalkanaで交換できないなら辞書から取り出す。
                after = dic.get(result)

            if not after:
                # もしalkanaにも辞書にもないなら読み方を取得する。
                url = f"https://www.sljfaq.org/cgi/e2k_ja.cgi?word={result.replace(' ', '+')}"
                async with self.session.get(url, headers=self.HEADERS) as r:
                    soup = BeautifulSoup(await r.text(), "html.parser")

                after = soup.find(class_='katakana-string').string.replace('\n', '')
                dic[result] = after

                async with async_open("cogs/tts/dic/dictionary.json", "w") as f:
                    await f.write(dumps(dic, indent=2, ensure_ascii=False))

            text = text.replace(result, after)
        return text


if __name__ == "__main__":
    async def run():
        session = ClientSession
        vm = VoiceManager(session, )
