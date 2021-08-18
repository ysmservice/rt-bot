# 読み上げで使える声の一覧です。

import cogs.tts.voiceroid as voiceroid


voices = {
    "mei": {
        "path": "cogs/tts/lib/OpenJTalk/mei.htsvoice",
        "name": "メイ",
        "description": 'Copyright (c) 2009-2018 Nagoya Insitute of Technology Department of Computer Science',
        "mode": "OpenJTalk"
    },
    "man": {
        "path": "cogs/tts/lib/OpenJTalk/nitech_jp_atr503_m001.htsvoice",
        "name": "男の人",
        "description": 'Copyright (c) 2003-2012 Nagoya Insitute of Technology Department of Computer Science',
        "mode": "OpenJTalk"
    },
    "reimu": {
        "path": "cogs/tts/lib/AquesTalk/f1/libAquesTalk.so",
        "name": "ゆっくり霊夢",
        "description": "AquesTalk 評価版, (株)アクエストの音声合成ライブラリAquesTalkによるものです。",
        "mode": "AquesTalk"
    },
    "marisa": {
        "path": "cogs/tts/lib/AquesTalk/f2/libAquesTalk.so",
        "name": "ゆっくり魔理沙",
        "description": "AquesTalk 評価版, (株)アクエストの音声合成ライブラリAquesTalkによるものです。",
        "mode": "AquesTalk"
    }
}
# Voiceroidをvoicesに追加する。
for key in voiceroid.VOICEROIDS:
    continue # まだベータだから
    voices[key] = {
        "path": key,
        "name": voiceroid.VOICEROIDS[key]["name"],
        "description": "VOICEROID デモ音声",
        "mode": "VOICEROID"
    }
