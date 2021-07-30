# RT Util - MySQL Manager

from typing import Union, Any, Dict, Tuple

from asyncio import AbstractEventLoop
from aiomysql import connect
import warnings
import ujson


warnings.filterwarnings('ignore', module=r"aiomysql")


class AlreadyPosted(Exception):
    pass


class Cursor:
    """データベースの操作を簡単に行うためのクラスです。  
    `Cursor.get_data`などの便利なものが使えます。  
    `MySQLManager.get_cursor`から取得することができます。
    このクラスは「`MySQLManager.get_cursor`から取得」と書きましたが、もちろん下にあるParametersを見て自分で定義することもできます。
    例：`cursor = Cursor(MySQLManager)`

    Notes
    -----
    

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
        `Cursor.prepare_cursor`を実行するまではこれは有効になりません。"""
    def __init__(self, db):
        self.cursor = None
        self.loop, self.connection = db.loop, db.connection

    async def prepare_cursor(self):
        """Cursorを使えるようにします。"""
        self.cursor = await self.connection.cursor()
        self.cursor._defer_warnings = True

    async def close(self):
        """Curosorを閉じます。"""
        if self.cursor is not None:
            await self.cursor.close()

    def __del__(self):
        self.loop.create_task(self.close())

    async def __aenter__(self):
        await self.prepare_cursor()
        return self

    async def __aexit__(self, ex_type, ex_value, trace):
        await self.cursor.close()

    async def create_table(self, table: str, columns: Dict[str, str],
                           if_not_exists: bool = True, commit: bool = True) -> None:
        """テーブルを作成します。

        Parameters
        ----------
        table : str
            テーブルの名前です。
        columns : Dict[str, str]
            作成する列の名前と型名の辞書です。  
            例：`{"name": "TEXT", "data": "TEXT"}`
        if_not_exists : bool, default True
            テーブルが存在しない場合作るようにするかどうかです。
        commit : bool, default True
            テーブルの作成後に自動で`MySQLManager.commit`をするかどうかです。"""
        if_not_exists = "IF NOT EXISTS " if if_not_exists else ""
        values = ", ".join(f"{key} {columns[key]}" for key in columns)
        await self.cursor.execute(f"CREATE TABLE {if_not_exists}{table} ({values})")
        del if_not_exists, values
        if commit:
            await self.connection.commit()

    async def drop_table(self, table: str, if_exists: bool = True, commit: bool = True) -> None:
        """テーブルを削除します。

        Parameters
        ----------
        table : str
            削除するテーブルの名前です。
        if_exists : bool, default True
            もしテーブルが存在するならテーブルを削除するかどうかです。
        commit : bool, default True
            テーブル削除後に自動で`MySQLManager.commit`を実行するかどうかです。"""
        if_exists = "IF EXISTS " if if_exists else ""
        await self.cursor.execute(f"DROP TABLE {if_exists}{table}")
        del if_exists
        if commit:
            await self.connection.commit()

    def _get_column_args(self, values: Dict[str, Any], format_text: str = "{} = %s AND") -> Tuple[str, list]:
        conditions, args = "", []
        for key in values:
            conditions += format_text.format(key)
            args.append(values[key])
        return conditions, args

    async def insert_data(self, table: str, values: Dict[str, Any], commit: bool = True) -> None:
        """特定のテーブルにデータを追加します。  

        Paremeters
        ----------
        table : str
            対象のテーブルです。
        values : Dict[str, Any]
            列名とそれに対応する追加する値です。  
            辞書は自動でjsonになります。
        commit : bool, default True
            追加後に自動で`MySQLManager.commit`を実行するかどうかです。  
            もし複数のデータを一度で追加する場合はこれを`False`にして終わった後に自分でcommitをしましょう。

        Examples
        --------
        async with db.get_cursor() as cursor:
            values = {"name": "Takkun", "data": {"detail": "愉快"}}
            await cursor.post_data("tasuren_friends", values)"""
        conditions, args = self._get_column_args(values, "{}, ")
        query = ("%s, " * len(args))[:-2]
        await self.cursor.execute(
            f"INSERT INTO {table} ({conditions[:-2]}) VALUES ({query})",
            [ujson.dumps(arg) if isinstance(arg, dict) else arg for arg in args]
        )
        if commit:
            await self.connection.commit()

    async def update_data(self, table: str, values: Dict[str, Any],
                          targets: Dict[str, Any], commit: bool = True) -> None:
        """特定のテーブルの特定のデータを更新します。

        Parameters
        ----------
        table : str
            対象のテーブルです。
        values : Dict[str, Any]
            更新する内容です。
        targets : Dict[str, Any]
            更新するデータの条件です。
        commit : bool, default True
            更新後に自動で`MySQLManager.commit`を実行するかどうかです。"""
        values, values_args = self._get_column_args(values)
        conditions, conditions_args = self._get_column_args(targets)
        await self.cursor.execute(
            f"UPDATE {table} SET {values[:-4]} WHERE {conditions[:-4]}",
            values_args + conditions_args
        )
        if commit:
            await self.connection.commit()

    async def exists(self, table: str, targets: Dict[str, Any]) -> bool:
        """特定のテーブルに特定のデータが存在しているかどうかを確認します。

        Parameters
        ----------
        table : str
            対象のテーブルです。
        targets : Dict[str, Any]
            存在確認をするデータの条件です。

        Returns
        -------
        exists : bool
            存在しているならTrue、存在しないならFalseです。"""
        return await self.get_data(table, targets) != []

    async def delete(self, table: str, targets: Dict[str, Any], commit: bool = True) -> None:
        """特定のテーブルにある特定のデータを削除します。

        Parameters
        ----------
        table : str
            対象のテーブルです。
        targets : Dict[str, Any]
            削除するデータの条件です。
        commit : bool, default True
            削除後に自動で`MySQLManager.commit`を実行するかどうかです。"""
        conditions, args = self._get_column_args(targets)
        await self.cursor.execute(
            f"DELETE FROM {table} WHERE {conditions[:-4]}",
            args
        )
        if commit:
            await self.connection.commit()

    async def get_datas(self, table: str, targets: Dict[str, Any]) -> list:
        """特定のテーブルにある特定の条件のデータを取得します。  
        見つからない場合は空である`[]`が返されます。  
        ジェネレーターです。

        Parameters
        ----------
        table : str
            対象のテーブルです。
        targets : Dict[str, Any]
            取得するデータの条件です。

        Returns
        -------
        data : list
            取得したデータのリストです。  
            yieldで返され`[なにか, なにか, なにか, なにか]`のようになっています。  
            もしjsonがあった場合は辞書になります。  
            見つからない場合は空である`[]`となります。"""
        conditions, args = self._get_column_args(targets)
        await self.cursor.execute(
            f"SELECT * FROM {table} WHERE {conditions[:-4]}", args)
        rows = await self.cursor.fetchall()
        if rows:
            for row in rows:
                datas = [ujson.loads(data) if data[0] == "{" and data[-1] == "}"
                         else data for data in row]
                yield datas
        else:
            yield []

    async def get_data(self, table: str, targets: Dict[str, Any]) -> list:
        """一つだけデータを取得します。  
        引数は`Cursor.get_datas`と同じです。

        Examples
        --------
        async with db.get_cursor() as cursor:
            targets = {"name": "Takkun"}
            row = await cursor.get_data("tasuren_friends", targets)
            if row:
                print(row[1])
                # -> "Takkun"
                print(row[-1])
                # -> {"detail": "愉快"} (辞書データ)"""
        conditions, args = self._get_column_args(targets)
        await self.cursor.execute(
            f"SELECT * FROM {table} WHERE {conditions[:-4]}", args)
        row = await self.cursor.fetchone()
        if row:
            return [ujson.loads(data) if data[0] == "{" and data[-1] == "}"
                    else data for data in row]
        else:
            return []


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
    def __init__(self, loop: AbstractEventLoop, user: str, password: str, db_name: str = "mysql",
                 port: int = 3306, host: str = "localhost"):
        loop.create_task(self._setup(user, password, loop, db_name, port, host))

    async def _setup(self, user, password, loop, db, port, host) -> None:
        # データベースの準備をする。
        self.loop = loop
        self.connection = await connect(host=host, port=port,
                                        user=user, password=password,
                                        db=db, loop=loop,
                                        charset="utf8")
        cur = await self.connection.cursor()
        await cur.close()

    async def commit(self):
        """変更をセーブします。"""
        await self.connection.commit()

    def get_cursor(self) -> Cursor:
        """データベースの操作を楽にするためのクラスのインスタンスを取得します。"""
        cursor = Cursor(self)
        return cursor

    def close():
        self.__del__()

    def __del__(self):
        self.connection.close()
