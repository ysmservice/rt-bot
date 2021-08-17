# 読み上げ (tts)
## ファイルマップ
### dic
辞書などを入れるフォルダです。
#### gime
https://github.com/KEINOS/google-ime-user-dictionary-ja-en/tree/master/Google-ime-jp-カタカナ英語辞典  
にあるものです。  
英語を読みのひらがなに置き換えるための辞書です。
#### allow_characters.csv
ゆっくりの読み上げで有効な文字です。  
空白で区切ります。
#### dictionary.json
グローバルな辞書です。  
自分の好きな単語をしっかり言わせたい時はこれを変更しましょう。  
なおdic/gimeの辞書になかった英単語の読みはウェブから持ってきてdictionary.jsonに書き込まれます。
### lib
#### AquesTalk
* f1 - ゆっくり霊夢
* f2 - ゆっくり魔理沙
#### OpenJTalk
htsvoiceのファイルを入れるば場所です。
### aquestalk.py
AquesTalkの簡易ラッパーです。
### openjtalk.py
OpenJTalkの簡易ラッパーです。
### voiceroid.py
VOICEROIDデモ音源生成APIの簡易ラッパーです。
### voice_manager.py
音声合成を簡単に行うためのモジュールです。
### data_manager.py
読み上げのセーブデータを簡単に管理するためのモジュールです。
### outputs
作った音声ファイルを保存する場所です。
