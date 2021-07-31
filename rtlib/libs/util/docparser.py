# rtlib.libs.util - Doc Parser

from typing import Literal, Optional, Callable, Tuple


class DocParser:
    """ドキュメントをパースするためのクラスです。"""

    HEADDINGS = {
        "Parameters": "# コマンドの引数",
        "Notes": "# メモ",
        "Warnings": "# 警告",
        "Examples": "# コマンドの使用例",
        "Raises": "# 起こり得るエラー",
        "Returns": "# 実行結果",
        "See Also": "# 関連事項"
    }
    ITEM_REPLACE_TEXTS = {
        "str": "文字列",
        "int": "整数",
        "float": "小数",
        "bool": "真偽値",
        ", optional": ", オプション",
        ", default": ", デフォルト"
    }

    def _split(self, text: str, target: str = ":") -> Tuple[str, str, int, int]:
        # targetの左と右を分けてtargetの周りにある空白の数を取得する。
        colon_index = text.find(":")
        left, right = text[:colon_index], text[colon_index + 1:]
        del colon_index
        left_count, right_count = 0, 0
        for i in range(len(left)):
            if left[0 - (i + 1)] == " ":
                left_count += 1
            else:
                break
        for char in right:
            if char == " ":
                right_count += 1
            else:
                break
        return (left[:0 - left_count], right[right_count:],
                left_count, right_count)

    def _colon_parser(self, line: str) -> str:
        # ITEM_REPLACE_TEXTSにある文字列は日本語に置き換える。
        for type_name in self.ITEM_REPLACE_TEXTS:
            if type_name in line:
                line = line.replace(type_name, self.ITEM_REPLACE_TEXTS[type_name])
        # 名前の部分を**で囲む。
        if ":" in line:
            left, right, left_count, right_count = self._split(line)
            return f"**{left}**{' '*left_count}:{' '*right_count}{right}"
        else:
            return f"**{line}**"

    def _item_parser(self, line: str, now: dict, before: dict) -> str:
        # 項目に含まれているものを最適なマークダウンに変換するものです。
        if now["item"] in ("Parameters", "Raises", "Returns", "See Also"):
            if  (all(char in self.indent_type for char in line[:self.indent])
                 if len(line) >= self.indent else line == ""):
                # 引数の説明。
                return line[self.indent:]
            else:
                # 引数の名前と型。
                return self._colon_parser(line)
        return line

    def parse(self, doc: str, *, first_indent_count: int = 1, indent: int = 4,
              indent_type: Literal[" ", "\t"] = " ",
              item_parser: Optional[Callable] = None) -> dict:
        """渡されたドキュメンテーションをマークダウンにパースします。

        Parameters
        ----------
        doc : str
            対象のドキュメンテーションです。
        first_indent_count : int, default 1
            ドキュメンテーションの最初にあるインデントの個数です。
        indent : int, default 4
            インデントの空白の数です。
        indent_type : Literal[" ", "\t"], default " "
            インデントに使われているの空白の文字です。
        item_parser : Optional[Callable[str, dict, dict]] = None
            項目をパースする際に使う関数です。  
            指定されなかった場合は`DocParser._item_parser`が使用されます。  
            カスタムしたい場合は`DocParser._item_parser`とか見て仕組み覗いて自分で作ろうね。

        Returns
        -------
        dict
            これは言語で分けられてパースしたドキュメンテーションを返すため辞書型となっています。  
            デフォルトの言語は`ja`となっています。"""
        item_parser = self._item_parser if item_parser is None else item_parser
        self.indent, self.indent_type = indent, indent_type

        text = {"ja": ""}
        before = {
            "line": "",
            "item": ""
        }
        now = {
            "lang": "ja",
            "item": "description"
        }

        for line in doc.splitlines():
            line = line[indent*first_indent_count:]
            if all(char == "-" for char in line) and line != "":
                # もし項目を分ける水平線だったら項目名をメモしておく。
                if before["line"].startswith("!lang "):
                    now["lang"] = before["line"][6:]
                    if now["lang"] not in text:
                        text[now["lang"]] = ""
                    now["item"] = "description"
                else:
                    before["item"] = now["item"]
                    now["item"] = before["line"]
                    t = self.HEADDINGS.get(now["item"], now["item"]) + "\n"
                    text[now["lang"]] += t
            elif line not in self.HEADDINGS and not line.startswith("!lang "):
                # 項目名などではない普通の場合はitem_paresrでアイテムをパースする。
                text[now["lang"]] += item_parser(line, now, before) + "\n"
            before["line"] = line
        return text


if __name__ == "__main__":
    doc = """
!lang ja
--------
これはテストドキュメンテーションテキストだよ。
気にしないでね。

Parameters
----------
test1 : str
    テスト１。
test2 : int
    テスト２。
test3 : str, default わお
    テスト３。

Examples
--------
これが例か...
いやこれなんだよ。

Raises
------
TestError : わお
HoiHoiError : ありゃしない

!lang en
--------
This is the test documentation text.
I wanna be the guy!

Parameters
----------
test1 : str
    test1
test2 : str

Notes
-----
Finish!
"""
    dp = DocParser()

    data = dp.parse(doc, first_indent_count=0)
    for key in data:
        print("-----", key, "------")
        print(data[key])
