# Free RT Util - Mine Sweeper Game Engine

from typing import Optional

import random

newlinestr = '\n'


class MineSweeper:

    def __init__(
            self, xlen: int, ylen: int, bombs: int, 
            seed: Optional[int] = None, log: bool = False
    ) -> None:
        "マインスイーパーです。インスタンス化でデータの作成までを行います。"
        if xlen > 100 or ylen > 100:
            raise ValueError("xlen and ylen must be 100 or less.")
        self.xlen: int = xlen
        self.ylen: int = ylen

        if bombs > (xlen * ylen):
            raise ValueError("bombs must be less than numbers of all squares.")
        self.bombs: int = bombs

        self.logging: bool = log
        if seed:
            random.seed(seed)
        self._make_data()
        self.now_opened = []

    def _make_data(self) -> None:
        # 初期データをself.dataに2次元配列で作成します。0~8の数字は回りにある爆弾の数、9は爆弾を表します。
        # 通常はこの関数はインスタンス時に自動で実行されます。
        raw_data = [0] * (self.xlen * self.ylen)
        for i in random.sample(range(self.xlen * self.ylen), k=self.bombs):
            raw_data[i] = 9

        # 2次元配列に直す。
        t_data = [
            [raw_data[x * self.ylen + y] for y in range(self.ylen)]
            for x in range(self.xlen)
        ]

        for x_checking in len(t_data):
            for y_checking in len(t_data[x_checking]):
                t_data[x_checking][y_checking] = \
                    self.get_around_data(t_data, x_checking, y_checking).count(9)

        self.data: tuple[tuple[int]] = tuple([tuple(i) for i in t_data])
        if self.logging:
            print(f"[util][MineSweeper]maked data: {newlinestr.join(self.data)}")

    def get_around_data(self, t_data, x, y) -> tuple[int]:
        "t_dataのx番目のy番目の周りの数(壁を越えていたら0)を取得したリストを返します。"
        if t_data[x][y] == 9:
            return (9, 9, 9, 9, 9, 9, 9, 9, 9)  # 9の数が9個なので問題ない。
        d = []

        for m in (
            (x - 1, y - 1), (x - 1, y), (x - 1, y + 1),
            (x, y - 1), (x, y), (x, y + 1),
            (x + 1, y - 1), (x + 1, y), (x + 1, y + 1)
        ):
            if -1 in m or len(t_data) + 1 == m[0] or len(t_data[x]) + 1 == m[1]:
                # 限界突破(壁を越えて判定している。)
                d.append(0)
            d.append(t_data[m[0]][m[1]])

        return tuple(d)

    def open(self, x: int, y: int) -> tuple[int]:
        """self.dataのx行目, y列目を取り出します。
        タプル型が返され、1番目が結果(0=操作完了, 1=クリア, 2=ゲームオーバー、3=すでに引いている)で、
        2番目が引いた数字になります。
        """
        assert x < self.xlen, "存在しない番地です。"
        assert y < self.ylen, "存在しない番地です。"
        # 実際のコマンドでは、この2つはコマンド処理側ではじかれるのでエラーは出ない。

        number = self.data[x][y]
        if self.logging:
            print(f"[util][Minesweeper] opened x : {x}, y : {y} -> {number}")

        if (x, y) in self.now_opened:
            # もう引いている。
            return (3, number)

        self.now_opened.append((x, y))

        if number == 9:
            # 爆弾を引いてゲームオーバー。
            return (2, number)
        elif len(self.now_opened) == (self.xlen * self.ylen - self.bombs):
            # 爆弾以外すべて引いたのでゲームクリア。
            return (1, number)
        else:
            # ゲームは続行。
            return (0, number)

    def to_string(self, mode: str = "s") -> str:
        "現在の状況をEmbedのdescriptionに表示する形式の文字列に変換します。"
        return "\n".join(
            ("`" + "` `".join(
                ["💣" if x == 9 else x if x in self.now_opened else "■" for x in l]
                if mode == "s" else ["💣" if x == 9 else x for x in l]
            ) + "`") for l in [list(i) for i in self.data]
        )
