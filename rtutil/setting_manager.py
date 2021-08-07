# rtutil - Setting Manager

from discord.ext import commands
import discord

from typing import (TypedDict, Literal, Optional, Callable,
                    Type, List, Dict)
from sanic import response, exceptions
from asyncio import create_task
from functools import wraps

from rtlib import OAuth, WebManager


class SettingItem(TypedDict):
    """設定項目のベースクラスです。"""
    item_type: Literal["text", "check", "radios"]

class SettingCheck(SettingItem):
    """設定項目のチェックボックスのクラスです。"""
    checked: bool # 初期値または更新後の値

class SettingTextBox(SettingItem):
    """設定項目のテキストボックスのクラスです。"""
    multiple_line: bool # 改行も含めることができるかどうか。
    text: str           # 初期値または更新後の値

class SettingRadio(TypedDict):
    """設定項目のラジオボタン単体のクラスです。"""
    checked: bool # 初期値または更新後の値
    name: str     # ラジオボタンにつける名前

class SettingRadios(SettingItem):
    """設定項目の複数のラジオボタンのクラスです。"""
    radios: List[SettingRadio] # SettingRadioの集まり。

class SettingData(TypedDict):
    """設定のデータのクラス。"""
    name: str
    description: str
    permissions: Optional[List[str]] # これとひとつ下のOptionalはなくてもいいということではないです。
    callback: Optional[Callable]     # APIから取得する際はこれはないということです。
    items: List[Type[SettingItem]]


class SettingManager(commands.Cog):

    ITEMS = {
        "text": "text",
        "check": "checked",
        "radios": "radios"
    }
    NOT_FOUND_SETTING = "({}なんて設定は)ないです。(NYN姉貴風)"

    def __init__(self, bot):
        self.bot = bot
        if "OnCommandAdd" not in self.bot.cogs:
            raise Exception("SettingManagerはrtlib.ext.on_command_addが必要です。")
        self.data: Dict[Literal["guild", "user"], Dict[str, SettingData]] = {"guild": {}, "user": {}}

    @staticmethod
    def setting(name: str, description: str, permissions: List[str],
                items: Dict[str, Type[SettingItem]], callback: Callable) -> Callable:
        """設定コマンドにつけるデコレータです。  
        これを付けると自動でウェブの設定画面に設定項目が追加されます。
        
        Parameters
        ----------
        mode: Literal["guild", "user"]
            設定の種類です。
        name : str
            設定の項目の名前です。
        description : str
            設定の説明です。
        items : Dict[str, Type[SettingItem]]
            設定の項目に入れるものです。
        callback : Callable
            設定変更時または設定読み込み時に呼び出される関数です。  
            `write/read, {item_name: content}`が渡されます。(contentはアイテムの種類です。)"""
        def decorator(coro):
            # デコレータを付けた関数にコマンド追加時に設定コマンドだと検知,情報取得ができるようにする。
            coro._rtutil_setting: SettingData = {
                "name": name,
                "description": description,
                "permissions": permissions,
                "callback": callback,
                "items": items
            }
            return coro
        return decorator

    @commands.Cog.listener()
    async def on_command_add(self, command):
        # コマンドが追加された時呼び出される関数です。
        if (data := command.getattr("_rtutil_setting", {})):
            # もし`setting`のデコレータが付いているなら`_rtutil_setting`があるはず。
            # それがあるならば設定リストに情報を追加しておく。
            self.data[data["mode"]][data["name"]] = {}
            self.data[data["mode"]][data["name"]].update(data)
            del self.data[data["mode"]][data["name"]]["mode"]
            del self.data[data["mode"]][data["name"]]["name"]
            del data

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        # コマンドが削除された時呼び出される関数です。
        # 設定リストに追加されているものなら削除する。
        if (data := command.getattr("_rtutil_setting", {})):
            if data["name"] in self.data[data["mode"]]:
                del self.data[data["mode"]][data["name"]], data

    def check_permissions(self, member: discord.Member, permissions: List[str]) -> bool:
        # 権限を持っているか確認をする。
        return all(getattr(member.guild_permissions, permission_name)
                   for permission_name in permissions)

    async def replace_default(self, cmd_data: SettingData) -> SettingData:
        # 渡されたコマンドの設定の構成データにある設定項目のデフォルトを設定します。
        for key in cmd_data["items"]:
            default = self.ITEMS[cmd_data[key]["name"]]
            cmd_data[key][default] = await cmd_data["callback"](
                "read", cmd_data[key]["name"],
                cmd_data[key][default]
            )
        del cmd_data["callback"]
        return cmd_data

    @commands.Cog.route("/api/settings/<mode>", methods=["GET"])
    @WebManager.cooldown(5)
    @OAuth.login_want()
    async def settings(self, request, mode):
        """設定の項目のリストを全て取得します。
        # URI:/api/setting/<mode>
        - mode : Literal["guild", "user"]
        > 取得する設定のモードです。guildの場合はサーバーの設定一覧です。userの場合はユーザーです。
        # レート制限
        5秒です。
        # 返り値
        ## guild
        {
            "status": "ok",
            "settings": {
                "サーバーID": {
                    "commands": {
                        "設定名(基本的にコマンド名)": {
                            "name": "設定名",
                            "description": "設定の説明",
                            "items": {
                                "設定項目名": {
                                    "item_type": "設定項目の種類 (text, check, radios)"
                                    // あとはその設定項目によって異なるものです。
                                    // これはこのファイルの上の方に形式が定義されています。
                                    // なのでフロントエンド開発者はそちらを見ましょう。
                                }
                            }
                        }
                    }
                }
            }
        }"""
        return_data = {"status": "ok", "settings": {}}
        if request.ctx.user:
            user = request.ctx.user

            if mode == "guild":
                data = self.data["guild"]

                # サーバーのIDと名前が必要だから一つづつguildを取り出す。
                for guild in self.bot.gulids:
                    if (member := guild.get_member(user.id)):
                        guild_id = str(guild_id)
                        # 返却するデータに設定項目の情報を追加できるように準備をしておく。
                        return_data["settings"][guild_id] = {"commands": {}, "name": guild.name}

                        # 設定が必要な項目を一つづつ取り出す。
                        for command_name in data:
                            # 権限を持っているなら設定項目を追加する。
                            if self.check_permissions(member, data[command_name]["permissions"]):
                                # 設定項目で既に設定されているものがあると思うのでそれのために返却するデータにデフォルトの設定をしておく。
                                return_data["settings"][guild_id]["commands"][command_name] = \
                                    await self.replace_default(data[command_name])
                        
                        # もし設定が空ならそのguild_idの辞書を削除する。
                        if not return_data["settings"][guild_id]["commands"]:
                            del return_data["settings"][guild_id]["commands"]
            elif mode == "user":
                # ユーザーのモードの設定を全て入れる。
                # もちろん既に設定されてるやつはデフォルトの設定をしておく。
                for command_name in self.data["user"]:
                    return_data["settings"][command_name] = \
                        await self.replace_default(self.data["user"][command_name])
        else:
            return exceptions.SanicException(
                "君の名は。あいにくだけどログインしてる状態じゃないとこれ使えないんっス。",
                403
            )
        return response.json(data)

    @commands.Cog.route(
        "/api/settings/guild/<guild_id>",
        methods=["POST"])
    @WebManager.cooldown(5)
    @OAuth.login_want()
    async def update_setting(self, request, guild_id):
        """サーバーの設定を更新します。
        # URI:/api/settings/guild/<guild_id>
        - guild_id : int
        > 設定更新対象サーバーID
        # POSTするデータ (json)
        {
            "設定するコマンド名": {
                    "設定項目名": // 上の取得時の設定項目の更新後をここに入れる。
                    // ^- これがいくつか続く。
                }
            }
        }"""
        # ciYRAyZQ=3yl2kXjJI1yiczM0ejNyNzNVTNozM2jwkMjwIimb5St6ZEII1iFMnh4WVf=
        if (member := request.user):
            guild_id = int(guild_id)
            if (guild := self.bot.get_guild(guild_id)):
                member = guild.get_member(member.id)
                request_data: Dict[str, Dict[str, Type[SettingItem]]] = request.json

                # 設定更新のリクエストをされているデータからコマンド名を一つづつ取り出す。
                for command_name in request_data:
                    if command_name not in self.data["guild"]:
                        raise exceptions.SanicException(
                            self.NOT_FOUND_SETTING.format(command_name), 404)

                    # 設定更新のリクエストをされているデータから
                    for item_name in request_data[command_name]:
                        data = request_data[command_name][item_name]

                        if item_name not in self.data["guild"][command_name]["items"]:
                            raise exceptions.SanicException(
                                self.NOT_FOUND_SETTING.format("設定項目" + item_name), 404)

                        self.data["guild"][command_name]["items"][item_name]

            else:
                raise exceptions.SanicException("そのサーバーっているんですかぁ？", 404)
        else:
            raise exceptions.SanicException("ログインしてね。", 403)


def setup(bot):
    bot.add_cog(SettingManager(bot))
