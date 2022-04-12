# RT util - Mine Sweeper Game Engine

from typing import Optional

import random


class MineSweeper:

    def __init__(
            self, xlen: int, ylen: int, bombs: int, 
            seed: Optional[int] = None, log: bool = False
    ):
        "マインスイーパーです。インスタンス化でデータの作成までを行います。"
        if xlen > 100 or ylen > 100:
            raise ValueError("xlen and ylen must be 100 or less.")
        self.xlen, self.ylen = xlen, ylen

        if bombs > (xlen * ylen):
            raise ValueError("bombs must be less than numbers of all squares.")
        self.bombs = bombs

        self.logging = log
        if seed:
            random.seed(seed)
        self.make_data()

    def make_data(self):
        "初期データをself.dataに2次元配列で作成します。0~8の数字は回りにある爆弾の数、9は爆弾を表します。"
        raw_data = [0] * (self.xlen * self.ylen)
        for i in random.sample(range(self.xlen * self.ylen), k=self.bombs):
            raw_data[i] = 9
        # 2次元配列に直す。
        t_data = [
            [raw_data[x*y] for y in range(self.ylen)]
            for x in range(self.xlen)
        ]
        for x_checking in len(t_data):
            for y_checking in len(t_data[x_checking]):
                t_data[x_checking][y_chexking] = \
                    self.get_around_data(t_data, x_checking, y_checking).count(9)
        self.data = t_data


    def get_around_data(self, t_data, x, y):
        "t_dataのx番目のy番目の周りの数(壁を越えていたら0)を取得したリストを返します。"
        if t_data[x][y] == 9:
            return (9, 9, 9, 9, 9, 9, 9, 9, 9)  # 9の数が9個なので問題ない。
        d = []

        for m in (
            (x-1, y-1), (x-1, y), (x-1, y+1),
            (x, y-1), (x, y), (x, y+1),
            (x+1, y-1), (x+1, y), (x+1, y+1)
        ):
            if -1 in m or len(t_data)+1 == m[0] or len(t_data[x])+1 == m[1]:
                # 限界突破(壁を越えて判定している。)
                d.append(0)
            d.append(t_data[m[0]][m[1]])

        return d




