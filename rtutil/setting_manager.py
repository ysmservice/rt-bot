# rtutil - Setting Manager

from discord.ext import commands
import discord

from typing import (TypedDict, Literal, Optional, Union,
                    Callable, Coroutine, Type, Any, Tuple, List, Dict)
from sanic import response, exceptions
from asyncio import create_task
from functools import wraps
from copy import copy

from rtlib import OAuth, WebManager
from data import get_headers


class SettingItem(TypedDict):
    """設定項目のベースの型です。"""
    item_type: Literal["text", "check", "radios", "list"]

class SettingCheck(SettingItem):
    """設定項目のチェックボックスの型です。"""
    checked: bool # チェックされているかどうか。

class SettingTextBox(SettingItem):
    """設定項目のテキストボックスの型です。"""
    multiple_line: bool # 改行も含めることができるかどうか。これが存在しない際はFalse
    text: str           # 値

class SettingList(SettingItem):
    """設定項目のリストボックスの型です。"""
    index: int # 現在選択されているものの番号。
    texts: Union[List[str], Tuple[str, ...]]

class InitSettingData(TypedDict):
    """設定のデータの型。デコレータのSettingManager.settingから生成されるもの。"""
    permissions: List[str]
    callback: Callable
    cog: Optional[Type[commands.Cog]]
    description: Union[str, Dict[str, str]]
    items: Dict[str, str]

class SettingData(TypedDict):
    """InitSettingDataのAPIから返される版です。(/api/settings/<Literal["guild", "user"]>)"""
    description: str
    items: Dict[str, Type[SettingItem]]


def logined_require(coro: Callable) -> Callable:
    # ログインしていないならエラーにするようにするデコレータ。
    @wraps(coro)
    async def new(self, request, *args, **kwargs):
        if request.ctx.user:
            return await coro(self, request, *args, **kwargs)
        else:
            raise exceptions.SanicException(
                "(ログインして)ないです。(NYN姉貴風)", 403)
    return new


class SettingManager(commands.Cog):

    # 設定項目の名前とそれに対応する重要キー
    ITEMS = {
        "text": "text",
        "check": "checked",
        "radios": "radios",
        "list": "list"
    }
    NOT_FOUND_SETTING = "({}なんて設定は)ないです。(NYN姉貴風)"

    def __init__(self, bot):
        self.bot = bot
        if "OnCommandAdd" not in self.bot.cogs:
            raise Exception("SettingManagerはrtlib.ext.on_command_addが必要です。")
        self.data: Dict[Literal["guild", "user"], Dict[str, InitSettingData]] = \
            {"guild": {}, "user": {}}

    @staticmethod
    def setting(mode: Literal["guild", "user"], name: str,
                description: Union[str, Dict[str, str]],
                permissions: List[str], callback: Callable,
                items: Dict[str, Union[str, Dict[str, str]]]) -> Callable:
        """設定コマンドにつけるデコレータです。  
        これを付けると自動でウェブの設定画面に設定項目が追加されます。

        Parameters
        ----------
        mode: Literal["guild", "user"]
            設定の種類です。
        name : str
            設定の項目の名前です。
        description : Union[str, Dict[str, str]]
            設定の説明です。  
            言語コードとその言語に対応する説明の辞書にすることで多言語に対応することができます。
        permissions : List[str]
            この設定を使うのに必要な権限の名前のリストです。
        callback : Callable
            設定変更時または設定読み込み時に呼び出される関数です。  
            `write/read, {item_name: content}`が渡されます。(contentはアイテムの種類です。)
        items : Dict[str, Union[str, Dict[str, str]]]
            設定の項目に入れるものです。  
            `{"項目の種類:項目名": "ウェブで表示される項目の名前"}`  
            項目名は設定更新/読み込み時になんの項目か判断するためのものです。  
            `ウェブで表示される項目の名前`を辞書にしてキーを言語コードにすれば多言語化できます。"""
        def decorator(coro):
            # デコレータを付けた関数にコマンド追加時に設定コマンドだと検知,情報取得ができるようにする。
            coro._rtutil_setting: InitSettingData = {
                "description": description,
                "permissions": permissions,
                "callback": callback,
                "cog": None,
                "items": items
            }
            coro._rtutil_setting_data = (mode, name)
            return coro
        return decorator

    @commands.Cog.listener()
    async def on_command_add(self, command):
        # コマンドが追加された時呼び出される関数です。
        if (data := getattr(command.callback, "_rtutil_setting", {})):
            # もし`setting`のデコレータが付いているなら`_rtutil_setting`があるはず。
            # それがあるならば設定リストに情報を追加しておく。
            mode, name = command.callback._rtutil_setting_data
            data["cog"] = command.cog
            self.data[mode][name] = {}
            self.data[mode][name].update(data)

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        # コマンドが削除された時呼び出される関数です。
        # 設定リストに追加されているものなら削除する。
        if (data := getattr(command, "_rtutil_setting", {})):
            if data["name"] in self.data[data["mode"]]:
                del self.data[data["mode"]][data["name"]], data

    def check_permissions(self, member: discord.Member, permissions: List[str]) -> bool:
        # 権限を持っているか確認をする。
        return all(getattr(member.guild_permissions, permission_name)
                   for permission_name in permissions)

    @staticmethod
    async def anext(coro: Coroutine, default: Any = Exception):
        # nextを非同期版で使うための関数です。run_callbackで使用した。
        try:
            return await coro.__anext__()
        except StopAsyncIteration as e:
            if isinstance(default, Exception):
                raise e
            else:
                return default

    async def run_callback(
                self, mode: Literal["guild", "user"], command_name: str,
                coro: Callable, args: Union[list, tuple], create_task_: bool = False
            ) -> Optional[Dict[str, Type[SettingItem]]]:
        # コールバックは走らせるための関数です。
        # セーブかどうかがわかるように。
        # もしコグにあるコールバックならselfを渡す必要があるから、コマンド追加時に保存していたコグを渡す。
        cog = self.data[mode][command_name]["cog"]
        if cog:
            args = [cog] + list(args) if isinstance(args, tuple) else args
        # コルーチンを作る。
        coro = coro(*args)
        # 走らせる。
        if create_task_:
            data = await self.anext(coro, None)
            if isinstance(data, dict):
                raise exceptions.SanicException(
                    message=data.get(self.bot.cogs["Language"].get(args[0].author.id),
                                     data["ja"]),
                    status_code=500
                )
            else:
                yield data
        else:
            async for result in coro:
                yield result

    def _replace_language_dict(self, data: dict, key: str, lang: str) -> dict:
        # 渡された辞書の指定されたキーにあるやつをlangの言語に置き換えれるなら置き換える。
        if isinstance(data[key], dict):
            data[key] = data[key].get(lang, data[key]["ja"])
        return data

    def replace_language(self, data: InitSettingData, user_id: int) -> dict:
        # 渡されたInitSettingDataにある言語を渡されたユーザーIDのユーザーの設定してる言語に置き換える関数。
        # 説明が多言語対応しているなら置き換えれないか試みる。
        lang = self.bot.cogs["Language"].get(user_id)
        data = self._replace_language_dict(data, "description", lang)
        # 設定項目の名前やラジオボタンの名前などを置き換えれないか試みる。
        for item_name in list(data["items"].keys()):
            # アイテムの説明を別言語に置き換えれそうなら置き換える。
            if not isinstance(data["items"][item_name], str):
                data["items"] = self._replace_language_dict(
                    data["items"], item_name, lang)

            if lang != "ja":
                # アイテムにある置き換えることのできも文字列を置き換えようと試みる。
                if item_name.startswith("radios"):
                    for radio in list(data["items"][item_name].keys()):
                        data["items"][item_name][radio] = \
                            self._replace_language_dict(
                                data["items"][item_name][radio],
                                "name", lang
                            )
        return data

    async def replace_default(
            self, mode: Literal["guild", "user"], command_name: str,
            cmd_data: InitSettingData, ctx: Any) -> SettingData:
        # 渡されたコマンドの設定の構成データにある文字列を最適げ言語に交換します。
        # それと構成データの設定項目のデフォルトを設定します。
        new_cmd_data = self.replace_language(copy(cmd_data), ctx.author.id)
        original_items, i = list(new_cmd_data["items"].items()), -1

        new_cmd_data["items"] = {
            original_items[(i := i + 1)][0][(sp := original_items[i][0].find(":")) + 1:]: {
                "item_type": (item_type := original_items[i][0][:sp]),
                self.ITEMS[item_type]: result,
                "display_name": original_items[i][1]
            }
            async for result in self.run_callback(
                mode, command_name, new_cmd_data["callback"],
                (ctx, "read", (key for key, _ in original_items))
            )
        }

        # APIから返す際にいらないものを削除しておく。
        del new_cmd_data["callback"], new_cmd_data["cog"], cmd_data
        new_cmd_data.pop("permissions", None)
        return new_cmd_data

    @commands.Cog.route("/api/settings/<mode>", methods=["GET"])
    @WebManager.cooldown(1)
    @OAuth.login_want()
    async def settings(self, request, mode):
        """設定の項目のリストを全て取得します。modeはguildかuserです。ログインしている必要があります。"""
        return_data = {"status": "ok", "settings": {}}
        if request.ctx.user:
            user = request.ctx.user

            if mode == "guild":
                data: Dict[str, InitSettingData] = self.data["guild"]

                # サーバーのIDと名前が必要だから一つづつguildを取り出す。
                for guild in self.bot.guilds:
                    if (member := guild.get_member(user.id)):
                        guild_id, ctx = str(guild.id), type(
                            "Context", (), {"guild": guild, "author": member})

                        # 返却するデータに設定項目の情報を追加できるように準備をしておく。
                        return_data["settings"][guild_id] = {
                            "commands": {},
                            "name": guild.name,
                            "icon": str(guild.icon.url) if guild.icon else None
                        }

                        # 設定が必要な項目を一つづつ取り出す。
                        for command_name in data:
                            # 権限を持っているなら設定項目を追加する。
                            if self.check_permissions(member, data[command_name]["permissions"]):
                                # 設定項目で既に設定されているものがあると思うのでそれのために返却するデータにデフォルトの設定をしておく。
                                return_data["settings"][guild_id] \
                                    ["commands"][command_name] = \
                                    await self.replace_default(
                                        "guild", command_name,
                                        data[command_name], ctx
                                    )
                        
                        # もし設定が空ならそのguild_idの辞書を削除する。
                        if not return_data["settings"][guild_id]["commands"]:
                            del return_data["settings"][guild_id]
            elif mode == "user":
                # ユーザーのモードの設定を全て入れる。
                # もちろん既に設定されてるやつはデフォルトの設定をしておく。
                ctx = type("Context", (), {"author": user, "user": user})

                for command_name in self.data["user"]:
                    return_data["settings"][command_name] = \
                        await self.replace_default(
                            "user", command_name,
                            self.data["user"][command_name], ctx
                        )
        else:
            return exceptions.SanicException(
                "君の名は。あいにくだけどログインしてる状態じゃないとこれ使えないんっス。",
                403
            )
        return response.json(
            return_data, headers=get_headers(self.bot, request)
        )

    async def _update_setting(
            self, mode: Literal["guild", "user"],
            request_data: Dict[str, Dict[str, Type[SettingItem]]],
            ctx_attrs: Dict[str, Union[discord.Member, discord.Guild]]) -> None:
        # 設定を更新するためのコルーチン関数。
        # 設定更新のリクエストをされているデータからコマンド名を一つづつ取り出す。
        for command_name in request_data:
            if command_name not in self.data[mode]:
                raise exceptions.SanicException(
                    self.NOT_FOUND_SETTING.format(command_name), 404)

            # もしmodeがguildなら設定変更ができるか権限チェックを行う。
            if mode == "guild":
                if not self.check_permissions(
                        ctx_attrs["author"], self.data[mode][command_name]["permissions"]):
                    raise exceptions.SanicException(
                        f"(あなたに{command_name}の設定を変える権限は)ないです。(NYN姉貴風)", 403)

            # 設定の更新を行う。
            await self.run_callback(
                mode, command_name,
                self.data[mode][command_name]["callback"],
                (type("Context", (), ctx_attrs), "write",
                 ((key, request_data[command_name][key] \
                     [self.ITEMS[request_data[command_name][key]["item_type"]]])
                  for key in request_data[command_name])
                ), True
            ).__anext__()

    @commands.Cog.route(
        "/api/settings/update/guild/<guild_id>",
        methods=["POST"])
    @WebManager.cooldown(5)
    @OAuth.login_want()
    @logined_require
    async def update_setting_guild(self, request, guild_id):
        """サーバーの設定を更新します。ログイン済みの必要があります。"""
        # ciYRAyZQ=3yl2kXjJI1yiczM0ejNyNzNVTNozM2jwkMjwIimb5St6ZEII1iFMnh4WVf=
        guild_id = int(guild_id)
        if (guild := self.bot.get_guild(guild_id)):
            if not (member := guild.get_member(request.ctx.user.id)):
                raise exceptions.SanicException("...誰？", 403)
            # 設定を更新する。
            await self._update_setting(
                "guild", request.json,
                {"guild": guild, "author": member})
            del guild, member
            return response.json(
                {"status": "ok"}, headers=get_headers(self.bot, request)
            )
        else:
            raise exceptions.SanicException(
                "(そのサーバーが見つから)ないです。(NYN姉貴風)", 404)

    @commands.Cog.route(
        "/api/settings/update/user",
        methods=["POST"])
    @WebManager.cooldown(5)
    @OAuth.login_want()
    @logined_require
    async def update_setting_user(self, request):
        """"サーバーの設定を更新します。
        POSTするデータは上と同じでログインしている必要があります。"""
        user = request.ctx.user
        await self._update_setting("user", request.json, {"author": user})
        return response.json(
            {"status": "ok"}, headers=get_headers(self.bot, request)
        )


def setup(bot):
    bot.add_cog(SettingManager(bot))
