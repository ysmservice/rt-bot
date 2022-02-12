# RT TTS - Agents

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Literal, Union
from enum import Enum

from subprocess import Popen, TimeoutExpired, PIPE
from asyncio import get_running_loop
from os.path import exists

from re import sub, findall

import discord

from jishaku.functools import executor_function

from pyopenjtalk import g2p
from gtts import gTTS

from aiofiles import open as aioopen
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from ujson import load, dumps

if TYPE_CHECKING:
    from . import TTSCog


ENG2KANA_DATA_PATH = "cogs/tts/data/eng2kana.json"
"英語からカタカナに変換されている辞書があるJSONファイルです。"
AQUESTALK_DIRECTORY = "cogs/tts/lib/AquesTalk"
"AquesTalkのプログラムが入っているフォルダです。"
OPENJTALK = "open_jtalk"
"なんのコマンドでOpenJTalkを実行するかです。"
OPENJTALK_DICTIONARY = "cogs/tts/lib/OpenJTalk/dic"
"OpenJTalkで使う辞書がある場所です。"
OPENJTALK_VOICE_DIRECTORY = "cogs/tts/lib/OpenJTalk"
"OpenJTalkで使う音声のデータがあるディレクトリです。"
AGENTS_JSON = "cogs/tts/data/avaliable_voices.json"
"使用可能な音声の情報が書いてあるJSONファイルのパスです。"
AGENTS: dict[str, Agent]
"使用可能なAgentの辞書です。"


class VoiceTypes(Enum):
    "音声合成に使うものの列挙型です。"

    openjtalk = 1
    aquestalk = 2
    gtts = 3


Source = Union[discord.FFmpegOpusAudio, discord.FFmpegPCMAudio]


class Agent:
    "音声合成の音声のクラスです。"

    def __init__(self, type_: VoiceTypes, name: str, agent: str, details: str):
        self.type, self.name, self.agent, self.details = type_, name, agent, details

    async def synthe(self, text: str, path: str) -> Source:
        "音声合成を行います。"
        return globals()[self.type.name](text, path, self.agent)

    @staticmethod
    def from_agent_code(code: str) -> Agent:
        "`<<VoiceTypes>.name>-<Agent.agent>`の形式のコードからAgentを取得します。"
        return AGENTS[code]


with open(AGENTS_JSON, "r") as f:
    for type_, datas in load(f).items():
        for agent, data in datas.items():
            AGENTS[f"{type_}-{agent}"] = Agent(
                getattr(VoiceTypes, type_), data["name"], agent, data["details"]
            )


class SyntheError(Exception):
    "音声合成失敗時に発生するエラーです。"


@executor_function
def _synthe(log_name: str, commands: str, text: str):
    # 音声合成のコマンドを実行します。
    proc = Popen(commands, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    try:
        _, stderr_ = proc.communicate(bytes(text, encoding="utf-8"), 5)
    except TimeoutExpired:
        proc.kill()
        raise SyntheError(f"{log_name}: 音声合成に失敗しました。ERR:TimeoutExpired")
    else:
        if stderr_:
            raise SyntheError(f"{log_name}: 音声合成に失敗しました。ERR:{stderr_}")


# 英語とカタカナの辞書を読み込んでおく。
eng2kana: dict[str, str] = {}
if exists(ENG2KANA_DATA_PATH):
    with open(ENG2KANA_DATA_PATH, "r") as f:
        eng2kana.update(load(f))
else:
    # 存在しないなら空のものを作っておく。
    with open(ENG2KANA_DATA_PATH, "w") as f:
        f.write(r"{}")


async def _dumps_eng2kana_data():
    # eng2kanaのデータを保存します。
    async with aioopen(ENG2KANA_DATA_PATH, "w") as f:
        await f.write(dumps(eng2kana, indent=2, ensure_ascii=False))


HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0'}
"英語をカタカナに変換するのに使うウェブサイトへアクセスするのに使うヘッダー"
session = None
async def eng2kana(text: str) -> str:
    "渡された文字列にある英語をかなにします。"
    global session
    if session is None:
        session = ClientSession(
            loop=get_running_loop(), raise_for_status=True
        )

    text = text.replace("\n", "、").lower()

    # 英単語をカタカナにする。
    words = findall("[a-zA-Z]+", text)
    for word in words:
        # 既にある英語辞書から英単語を検索する。
        result = eng2kana.get(word)

        if result is None:
            # もしまだない英単語の場合は読み方の取得を行う。
            async with session.get(
                f"https://www.sljfaq.org/cgi/e2k_ja.cgi?word={result.replace(' ', '+')}", headers=HEADERS
            ) as r:
                eng2kana[word] = BeautifulSoup(await r.text(), "lxml") \
                    .find(class_='katakana-string').string.replace('\n', '')
            result = eng2kana[word]

            # 同期しておく。
            session.loop.create_task(_dumps_eng2kana_data(), name="TTS: Sync eng2kana data")

        text = text.replace(word, result)

    return text


NO_JOINED_TWICE_CHARS = (
    "ー", "、", "。", "っ", "ゃ", "ゅ", "ょ",
    "ッ", "ャ", "ュ", "ョ"
)
async def adjust_text(text: str) -> str:
    "日本語の文章をちょうどよく調整します。"
    if len(text) > 40:
        text = text[:41] + " いかしょうりゃく"
    # 二回連続の「っ」などを一つにする。
    for char in NO_JOINED_TWICE_CHARS:
        text = sub(f"{char}+", char, text)
    # 連続するwは一つにする。にする。
    text = sub("w{2,}", "わらわら", text)
    # 日本語の一部文字列を最適な文字列にする。
    text = text.replace("()", "かっこしっしょう")
    text = text.replace("(笑)", "かっこわらい")

    return await eng2kana(text)


def prepare_source(path: str) -> Source:
    "Sourceを作ります。"
    return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path)) \
        if discord.opus.is_loaded() else discord.FFmpegOpusAudio(path)


#   AquesTalk
with open("aquestalk_allowed_characters.csv", "r") as f:
    AQUESTALK_ALLOWED_CHARACTERS = f.read().split()
    "AquesTalkで使える文字のリスト"
AQUESTALK_REPLACE_CHARACTERS = {
    "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
    "ァ": "あ", "ィ": "い", "ゥ": "う", "ェ": "え", "ォ": "お"
}
"AquesTalkで読めない文字の置き換えに使う辞書"


@executor_function
def aiog2p(*args, **kwargs):
    "`run_in_executor_function`を使って非同期に実行できるようにした`pyopenjtalk.g2p`です。"
    return g2p(*args, **kwargs)


async def aquestalk(text: str, path: str, agent: Union[Literal["f1", "f2"], str]) -> Source:
    "AquesTalkで音声合成をします。"
    # 英語をかなに変換して残った感じ等もかなにする。
    text = await aiog2p(text, kana=True)

    # AquesTalk用に文字列を調整する。
    for char in AQUESTALK_REPLACE_CHARACTERS:
        text = text.replace(char, AQUESTALK_REPLACE_CHARACTERS[char])

    # 一番最初に存在しているNO_JOINED_TWICE_CHARSの文字を消す。
    new_text, first = "", True
    for char in text:
        if char in NO_JOINED_TWICE_CHARS:
            if first:
                continue
        elif first:
            first = False
        new_text += char

    # 読めない文字は消す。
    text = "".join(char for char in new_text if char in AQUESTALK_ALLOWED_CHARACTERS)

    # 音声合成をする。
    await _synthe(
        f"AquesTalk[{agent}]", f"./{f'{AQUESTALK_DIRECTORY}/{agent}'} 130 > {path}", text
    )

    return prepare_source(path)


#   OpenJTalk
async def openjtalk(text: str, path: str, agent:str) -> Source:
    "OpenJTalkで音声合成を行います。"
    await _synthe(
        f"OpenJTalk[{agent}]", f"""{OPENJTALK} -x {OPENJTALK_DICTIONARY}
 -m {f'{OPENJTALK_VOICE_DIRECTORY}/{agent}.htsvoice'} -r 1.0 -ow {path}""", text
    )
    return prepare_source(path)


#   gTTS
@executor_function
def _gtts(text: str, path: str, agent:str):
    gTTS(text, lang=agent).save(path)


async def gtts(text: str, path: str, agent:str) -> Source:
    "gTTSを使用して音声合成をします。"
    await _gtts(text, path, agent)
    return prepare_source(path)