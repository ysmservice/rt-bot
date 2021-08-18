# RT TTS - AquesTalk

from aiofiles import open as async_open
import asyncio

import ctypes


SyntheError = type("SyntheError", (Exception,), {})
libs = {}


def load_libs(paths: dict) -> None:
    """AquesTalkのライブラリを読み込みます。  
    読み込んだライブラリは`libs`に名前と一緒に辞書形式で保存されます。  
    `synthe`を使用する前にこれを実行しておいてください。

    Parameters
    ----------
    paths : Dict[str, str]
        読み込むAquesTalkのライブラリの名前とパスの辞書です。"""
    for name, path in paths.items():
        libs[name] = ctypes.cdll.LoadLibrary(path)


async def synthe(
        voice: str, file_path: str, text: str, speed: int = 130
    ) -> None:
    """AquesTalkを使用して音声合成を行います。　　
    使用するライブラリは`load_libs`で読み込んだものが使われます。

    Parameters
    ----------
    voice : str
        `libs`に読み込まれているライブラリの指定です。  
        `load_libs`で読み込むことができます。  
        例：`f1` (ゆっくり霊夢)
    file_path : str
        生成した音声データを書き込むファイルのパスです。
    text : str
        音声合成する文字列です。
    speed : int, default 180
        文字列を読むスピードです。

    Raises
    ------
    KeyError
        ライブラリが見つからない際に発生します。
    SyntheError
        音声合成が何かしらの理由で失敗した際に発生します。"""
    aqtk = libs[voice]

    # 音声合成をする。
    size_callback = ctypes.c_int(0)
    wav_address = aqtk.AquesTalk_Synthe(
        text.encode('cp932', errors='ignore'),
        speed, ctypes.byref(size_callback)
    )

    if not wav_address:
        # もし生成できない場合はエラーを起こす。
        print(text)
        raise SyntheError(f"音声合成に失敗しました。ERR:{size_callback.value}")

    # 音声データのunsigned *charをunsigned *byteにキャストする。
    wav_address = ctypes.cast(
        wav_address,
        ctypes.POINTER(
            ctypes.ARRAY(ctypes.c_ubyte, size_callback.value)
        )
    )

    # 音声データの中身をPythonのbytearray型にして書き込む。
    async with async_open(file_path, "wb") as f:
        await f.write(bytearray(wav_address.contents))

    # メモリにある音声データの領域をもう必要ないので解放する。
    aqtk.AquesTalk_FreeWave(wav_address)


if __name__ == "__main__":
    paths = {
        "f1": "cogs/tts/lib/f1/libAquesTalk.so",
        "f2": "cogs/tts/lib/f2/libAquesTalk.so"
    }
    load_libs(paths)
    asyncio.run(
        synthe(
            input("声種類："), "output.wav", input("文字列：")
        )
    )