# RT TTS - OpenJTalk

import asyncio


SyntheError = type("SyntheError", (Exception,), {})


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
    cmd = f"{open_jtalk} -x {dictionary} -m {voice} -r {speed} -ow {file_path}"
    # コマンドを実行する。
    proc = await asyncio.create_subprocess_shell(
        cmd, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # 実行結果を取得する。
    stdout, stderr = await proc.communicate(text.encode())
    # 実行結果を出力する。
    if stdout:
        print("OpenJTalk :", stdout)
    if stderr:
        raise SyntheError(f"音声合成に失敗しました。ERR:{stderr}")


if __name__ == "__main__":
    asyncio.run(
        synthe(
            "cogs/tts/lib/OpenJTalk/mei.htsvoice",
            "/var/lib/mecab/dic/open-jtalk/naist-jdic",
            "output.wav", input("文字列：")
        )
    )