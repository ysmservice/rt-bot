# RT TTS - OpenJTalk

from typing import Coroutine

from subprocess import Popen, TimeoutExpired, PIPE

from jishaku.functools import executor_function


SyntheError = type("SyntheError", (Exception,), {})


@executor_function
def _synthe(log_name: str, commands: str, text: str) -> Coroutine:
    # 音声合成を実行します。
    proc = Popen(commands, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    try:
        _, stderr_ = proc.communicate(bytes(text, encoding="utf-8"), 5)
    except TimeoutExpired:
        proc.kill()
        raise SyntheError(f"{log_name}: 音声合成に失敗しました。ERR:TimeoutExpired")
    else:
        if stderr_:
            raise SyntheError(f"{log_name}: 音声合成に失敗しました。ERR:{stderr_}")


async def synthe(
    voice: str, dictionary: str, file_path: str,
    text: str, speed: float = 1.0, open_jtalk = "open_jtalk"
) -> None:
    """OpenJTalkを使い音声合成をします。

    Parameters
    ----------
    voice : str
        使うhtsvoiceのパスです。
    dictionary : str
        使う辞書のパスです。
    file_path : str
        出力する音声のファイルのパスです。
    text : str
        読み上げる文字列です。です。
    speed : float, default 1.0
        読み上げるスピードです。です。
    open_jtalk : str, defalt "open_jtalk"
        OpenJTalkのパスです。"""
    # コマンドを実行する。
    return await _synthe(
        "OpenJTalk", f"{open_jtalk} -x {dictionary} -m {voice} -r {speed} -ow {file_path}", text
    )


if __name__ == "__main__":
    from asyncio import run
    run(
        synthe(
            "cogs/tts/lib/OpenJTalk/mei.htsvoice",
            "/var/lib/mecab/dic/open-jtalk/naist-jdic",
            "output.wav", input("文字列：")
        )
    )
