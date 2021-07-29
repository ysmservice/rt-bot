# RT Util - MySQL Manager

from typing import Union, Any, Dict, Tuple

from asyncio import AbstractEventLoop
from aiomysql import connect
import ujson


class AlreadyPosted(Exception):
    pass


class Cursor:
    """cursorを使ってやるデータベースの操作を簡単に行うためのクラスです。

    Parameters
    ----------
    db : MySQLManager
        データベースマネージャーです。

    Attributes
    ----------
    loop : asyncio.AbstractEventLoop
        イベントループです。
    connection
        データベースとの接続です。
    cursor
        データベースの操作などに使うカーソルです。  
        `Cursor.prepare_cursor`を実行するまではこれは有効になりません。

    Notes
    -----
    なにか操作をしたい場合は`Cursor.prepare_cursor`を実行する必要があります。  
    操作が終わったら`Cursor.close`を実行する必要があります。  
    そしてこのクラスは`async with`文を使うことができ、これを使うことで`Cursor.prepare_cursor`と`Cursor.close`を省くことができます。  
    もしこのクラスにある関数以外でなにかカスタムで実行したいことがあれば`Cursor.cursor`の`execute`などをを使用してください。"""
    def __init__(self, db: MySQLManager):
        self.loop, self.connection = db.loop, db.connection

    async def prepare_cursor(self):
        """Cursorを使えるようにします。"""
        self.cursor = await connection.cursor()

    async def close(self):
        """Curosorを閉じます。"""
        await self.cursor.close()

    def __del__(self):
        self.loop.create_task(self.cursor.close())

    async def __aenter__(self):
        await self.prepare_cursor()
        return self

    async def __aexit__(self, ex_type, ex_value, trace):
        await self.cursor.close()

    def _get_column_args(self, values: Dict[str, Any], format_text: str = "{} = ? AND") -> Tuple[str, list]:
        conditions, args = "", []
        for key in targets:
            conditions += format_text.format(key)
            args.append(targets[key])
        return conditions, args

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
        async with Cursor(db) as cursor:
            values = {"name": "Takkun", "data": {"detail": "愉快"}}
            await cursor.post_data("tasuren_friends", values)"""
        conditions, args = self._get_column_args(values, "{}, ")
        await self.curosr.execute(
            f"INSERT INTO {table} VALUES ({conditions[:-1]}) ('?, '*len(args))", args)
        if commit:
            await self.connection.commit()

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
        async with Cursor(db) as cursor:
            # ひとつだけ取得する。
            targets = {"name": "Takkun"}
            rows = await cursor.get_data("tasuren_friends", targets)
            if rows is not None:
                print(rows[0][1])
                # -> "Takkun"
                print(rows[0][-1])
                # -> {"detail": "愉快"} (辞書データ)"""
        conditions, args = self._get_column_args(targets)
        await self.cursor.exeute(
            f"SELECT * FROM {table} WHERE {conditions[:-4]}", args)
        rows = await self.cur.fetchone() if fetchall else await self.cur.fetchall()
        return [row[:-1] + ujson.loads(row[-1]) for row in rows]


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
        cursor = Cursor(self.loop)
        await cursor.prepare_cursor()
        return cursor

    def close():
        self.__del__()

    def __del__(self):
        self.connection.close()
