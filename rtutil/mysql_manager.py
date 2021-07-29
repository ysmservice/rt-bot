# RT Util - MySQL Manager

from typing import Any, Dict

from asyncio import AbstractEventLoop
from aiomysql import connect
import ujson


class AlreadyPosted(Exception):
    pass


class Cursor:
    @classmethod
    async def get_cursor(cls, loop, connection):
        """Cursorを取得します。"""
        cls.loop = loop
        cls.connection = connection
        cls.cursor = await connection.cursor()
        return cls

    async def post_data(self, table: str, values: Dict[str, Any], commit: bool = True) -> None:
        """特定のテーブルにデータを追加します。  

        Paremeters
        ----------
        table : str
            対象のテーブルです。
        values : Dict[str, Any]
            列名とそれに対応する追加する値です。
        commit : bool, default True
            追加後に自動で`MySQLManager.commit`を実行するかどうかです。  
            もし複数のデータを一度で追加する場合はこれを`False`にして終わった後に自分でcommitをしましょう。

        Examples
        --------
        cur = await db.get_cursor()
        values = {"name": "Takkun", "data": {"detail": "愉快"}}
        await cur.post_data("tasuren_friends", values)
        await cur.close()"""

    async def get_data(self, table: str, targets: Dict[str, Any], fetchall: bool = False) -> list:
        """特定のテーブルにある特定の条件のデータを取得します。  
        見つからない場合は空である`[]`が返されます。

        Parameters
        ----------
        table : str
            対象のテーブルです。
        targets : Dict[str, Any]
            条件に追加するものです。
        fetchall : bool, default False
            取得したものを全て取得するかどうかです。  
            Falseの場合は一つだけしか取得されません。

        Returns
        -------
        datas : list
            取得したデータのリストです。  
            `[[なにか, なにか, なにか, 辞書データ], ...]`のようになっています。  
            見つからない場合は空である`[]`となります。

        Examples
        --------
        cur = await db.get_cursor()
        # ひとつだけ取得する。
        targets = {"name": "Takkun"}
        rows = await cur.get_data("tasuren_friends", targets)
        if rows is not None:
            print(rows[0][1])
            # -> "Takkun"
            print(rows[0][-1])
            # -> {"detail": "愉快"} (辞書データ)
        await cur.close()"""
        conditions, args = "", []
        for key in targets:
            conditions += f"{key} = ? AND"
            args.append(targets[key])
        async with self.connection.cursor() as cur:
            await cur.exeute(
                f"SELECT * FROM {table} WHERE {conditions[:-4]}", args)
            rows = await cur.fetchone() if fetchall else await curs.fetchall()
        return [row[:-1] + ujson.loads(row[-1]) for row in rows]

    async def close(self):
        """Curosorを閉じます。"""
        await self.cursor.close()

    def __del__(self):
        self.loop.create_task(self.cursor.close())


class MySQLManager:
    """MySQLをRT仕様で簡単に使うためのモジュールです。  
    aiomysqlを使用しています。

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        イベントループです。
    user : str
        MySQLのユーザー名です。
    password : str
        MySQLのパスワードです。
    db_name : str, default "mysql"
        データベースの名前です。

    Attributes
    ----------
    connection
        aiomysqlのMySQLとのコネクションです。
    loop : asyncio.AbstractEventLoop
        使用しているイベントループです。

    Examples
    --------
    db = rtutil.MySQLManager(bot.loop, "root", "I wanna be the guy")"""
    def __init__(self, loop: AbstractEventLoop, user: str, password: str, db_name: str = "mysql"):
        loop.create_task(self._setup(user, password, loop, db_name))

    async def _setup(self, user, password, db) -> None:
        # データベースの準備をする。
        self.loop = loop
        self.connection = await connect(host="127.0.0.1", port=3306,
                                        user=user, password=password,
                                        db="mysql", loop=self.bot.loop,
                                        charset="utf8")
        cur = await self.connection.cursor()
        await cur.close()

    async def commit(self):
        """変更をセーブします。"""
        await self.connection.commit()

    async def get_cursor(self):
        """カーソルを取得します。"""
        return await Cursor.get_cursor(self.loop)

    def close():
        self.__del__()

    def __del__(self):
        self.connection.close()
