# rt-bot - コントリビューティングガイド
これはrt-botを開発する上でやって欲しいことを求めたものです。

## コミットメッセージ
なるべく以下のような感じにすると嬉しいです。
```md
# 新しく何かを作った場合
new: 内容

# 更新をした場合
update: 内容

# バグ修正をした場合
fix: 内容

# 何か変更をした場合
change: 内容
```
### 注釈
コミットメッセージの最初のタグ(`fix`や`new`など)の後に`[]`を使って以下のように注釈を付け加えるとより嬉しいです。
```md
# 文字列を変えただけの場合
change[text]: 内容

# ドキュメンテーションを変えただけの場合
change[doc]: 内容
```

## Pythonのコードの書き方
### 基本的な書き方
PEP8で文字数は90文字より少ない文字数にして欲しいです。  
ファイルの最初には以下のように`# RT - ファイルにあるものの名前`のようにつけて改行をして欲しいです。
```python
# RT - Help Command

...
```
### インポート
`import`は以下のように巨大なもので分けて行にある文字数の多さで並び替えをして欲しいです。  
ですが`typing`を入れる場合はそのインポートだけは一番上で`TYPE_CHECKING`は一番下がいいです。
```python
from typing import TYPE_CHECKING

from discord.ext import commands
import discord

from reprypt import decrypt
from ujson import loads

from .constants import DEFAULT

if TYPE_CHECKING:
    ...
```
### インデントがない場所のものは二行ずつ
クラスや関数などでインデントがない場所にあるものは以下のように二行ずつにして欲しいです。
```python
def test(...) -> ...:
    ...


class Wow:
    def huga(self, ...) -> ...:
        ...

    def test(self, ...) -> ...:
        ...
```
### ドキュメンテーション/アノテーション
色々な場所で使われるような関数には軽いドキュメンテーションとアノテーションをつけて欲しいです。  
内部的に使われるものには`_`を最初につけて関数のちょっとした説明を`#`のコメントで示して欲しいです。  
(アノテーションは不要です。)
```python
from typing import Optional


def encode(text: str) -> Optional[str]:
    "これは渡された文字列をエンコードする関数です。"
    ...


def _plus(text):
    # これは渡されたエンコードされた文字列を拡張するものです。
    ...
```
外部的に使われるような変数には型アノテーションをなるべくつけるようにしてください。  
もし汚くなるようでしたらクラス直下にアノテーションをつけた変数を列挙しましょう。  
DiscordのBotのコマンドの場合はアノテーションを書かなくても良いです。