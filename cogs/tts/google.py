# RT TTS - Google

from jishaku.functools import executor_function
from gtts import gTTS


@executor_function
def synthe(path: str, text: str):
    gTTS(text).save(path)