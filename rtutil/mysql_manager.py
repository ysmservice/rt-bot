# RT Util - MySQL Manager

from aiomysql import connect
import ujson


class MySQLManager:
    """MySQLをRT仕様で簡単に使うためのモジュールです。  
    注意：Botの起動が完了するまで使うことはできません。"""
    def __init__(self, bot, user: str, password: str):
        self.bot = bot
        self.__user, self.__password = user, password
        self.bot.add_listener(self._on_ready, "on_ready")

    async def _on_ready(self):
        # データベースの準備をする。
        self.connection = await connect(host="127.0.0.1", port=3306,
                                        user=user, password=password,
                                        db="mysql", loop=self.bot.loop,
                                        charset="utf8")
        cur = await self.connection.cursor()
        await cur.execute("CREATE TABLE IF NOT EXISTS UserData (UserID INTEGER, SettingName TEXT, Data TEXT)")
        await cur.execute("CREATE TABLE IF NOT EXISTS GuildData (UserID INTEGER, SettingName TEXT Data TEXT)")
        await self.connection.commit()
        await cur.close()

    async def get_userdata(self, user_id: int, setting_name: str) -> dict:
        """特定のユーザーデータを取得します。
        Parameters
        ----------
        usre_id : int
            対象のユーザーデータです。
        setting_name : str
            対象の設定名です。
 
        Returns
        -------
        data : dict
            取得したデータです。  
            もしデータが見つからない場合は空の`{}`となります。"""
        cur = await self.connection.cursor()
        await cur.execute("SELECT * FROM UserData WHERE UserID = ? AND SettingName = ?",
                          (user_id, setting_name))
        row = await cur.fetchone()
        return ujson.loads(row[-1]) if row else {}

    async def get_all_userdata(self, setting_name: str) -> dict:
        """対象の設定項目の設定をすべて取得します。
        Parameters
        ----------
        setting_name : str
            対象の設定名です。

        Returns
        -------
        data : 
            取得したデータです。  
            もしデータがみつからない場合は空の`()`です。"""

    def close():
        self.__del__()

    def __del__(self):
        self.connection.close()
