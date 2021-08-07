# rtutil - Setting Manager

from discord.ext import commands
import discord

from typing import (TypedDict, Literal, Union, Callable,
                    Union, List, Tuple, Dict, Type)
from sanic import response, exceptions
from asyncio import create_task

from rtlib import OAuth, WebManager


class SettingItem(TypedDict):
    """設定を構成するアイテムのベースクラスです。"""
    permissions: Union[List[str], Tuple[str, ...]]
    item_type: Literal["text", "check", "radios"]
    name: str

class SettingCheck(SettingItem):
    """設定項目のチェックボックスのクラスです。"""
    checked: bool

class SettingTextBox(SettingItem):
    """設定項目のテキストボックスのクラスです。"""
    default: str
    multiple_line: bool
    test: str

class SettingRadio(TypedDict):
    """設定項目のラジオボタン単体のクラスです。"""
    checked: bool
    name: str

class SettingRadios(SettingItem):
    """設定項目の複数のラジオボタンのクラスです。"""
    radios: List[SettingRadio]

class SettingData(TypedDict):
    """設定データの形式。bot.commandのextras["on_setting"]に入れるもの。"""
    description: str
    callback: Callable
    mode: Literal["guild", "user"]
    items: List[Type[SettingItem]]


class SettingManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if "OnCommandAdd" not in self.bot.cogs:
            raise Exception("SettingManagerはrtlib.ext.on_command_addが必要です。")
        self.data = {}
        self.cogs = {}

    @commands.Cog.listener()
    async def on_command_add(self, command):
        data: Union[SettingData, None] = command.extras.get("on_setting")
        if data:
            self.data[command.qualified_name] = data
            if command.cog is not None:
                self.cogs[command.qualified_name] = command.cog.__class__.__name__

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        if "on_setting" in command.extras:
            self.data.pop(command.qualified_name, None)

    def check_permissions(self, member: discord.Member, permissions: List[str]) -> bool:
        return all(getattr(member.guild_permissions, permission_name)
                   for permission_name in permissions)

    @commands.Cog.route("/api/settings/<mode>", methods=["GET"])
    @WebManager.cooldown(3)
    @OAuth.login_want()
    async def settings(self, request, mode):
        """設定の項目のリストを全て取得します。
        # URI:/api/setting/<mode>
        - mode : Literal["guild", "user"]
        > 取得する設定のモードです。guildの場合はサーバーの設定一覧です。userの場合はユーザーです。
        # レート制限
        3秒です。
        # 返り値
        {
            "status": "ok",
            "settings": {
                "サーバーID": {
                    "commands": {
                        "設定コマンド名": {
                            "items": [
                                {
                                    "permissions": ["権限名一覧"],
                                    "name": "設定項目名",
                                    "その他その項目の情報": "text, checkedなど"
                                } // このようなアイテムの項目が何個か。
                                  // これはユーザーが変更可能な設定のみです。
                                  // rtutil/setting_manager.pyの上の方にどんな形式なのかが書いてあります。
                            ],
                            "description": "コマンドの説明"
                        }
                    },
                    "name": "サーバー名"
                }
            }
        }"""
        data = {"status": "ok", "settings": {}}
        if request.ctx.user:# ciYRAyZQ=3yl2kXjJI1yiczM0ejNyNzNVTNozM2jwkMjwIimb5St6ZEII1iFMnh4WVf=
            user = request.ctx.user
            if mode == "guild":
                queue = []

                for guild in self.bot.guilds:
                    if (member := guild.get_member(user.id)):
                        guild_id = str(guild.id)
                        data["settings"][guild_id] = {"commands": {}, "name": guild.name}

                        for command_name in self.data:
                            data["settings"][guild_id]["commands"][command_name] = {
                                "items": {},
                                "description": self.data[command_name]["description"]
                            }
                            data["settings"][guild_id]["commands"][command_name]["items"] = [
                                item for item in self.data[command_name]["items"]
                                if self.check_permissions(member, item["permissions"])
                            ]

                            if not data["settings"][guild_id]["commands"][command_name]["items"]:
                                del data["settings"][guild_id]["commands"][command_name]
                        if not data["settings"][guild_id]["commands"]:
                            del data["settings"][guild_id]
            elif mode == "user":
                data["settings"] = {
                    command_name: self.data[command_name]["items"]
                    for command_name in self.data
                    if self.data[command_name]["mode"] == "user"
                }
        else:
            return exceptions.SanicException(
                "君の名は。あいにくだけどログインしてる状態じゃないとこれ使えないんっス。",
                403
            )
        return response.json(data)

    def pop_main(self, item: Type[SettingItem]) -> Union[bool, str, List[SettingRadio]]:
        if item["item_type"] == "text":
            return item["text"]
        elif item["item_type"] == "check":
            return item["checked"]
        elif item["item_type"] == "radios":
            return item["radios"]

    @commands.Cog.route(
        "/api/settings/guild/<guild_id>",
        methods=["POST"])
    @WebManager.cooldown(3)
    @OAuth.login_want()
    async def update_setting(self, request, guild_id):
        """設定を更新します。
        # URI:/api/settings/guild/<guild_id>
        - guild_id : int
        > 設定更新対象サーバーID
        # データ (json)
        {
            "設定するコマンド名": {
                [
                    // `/api/settings/<mode>`でもらった項目のデータの変更後のデータ。
                    // 変更されるのはtextやcheckedなど。
                ]
            }
        }"""
        if (member := request.user):
            guild_id = int(guild_id)
            if (guild := self.bot.get_guild(guild_id)):
                member = guild.get_member(member.id)
                request_data: Dict[str, Type[SettingItem]] = request.json

                for command_name in request_data:
                    data = self.data.get(command_name)

                    for item in request_data[command_name]:
                        if not self.check_permissions(
                                member,
                                data["items"][data["items"].index(item)]["permissions"]):
                            raise exceptions.SanicException("権限がないZOY！", 403)
                        if "callback" not in data:
                            raise exceptions.SanicException(
                                f"あれ？{command_name}のコールバックが見当たらない。"
                                + "悪いけど設定更新できないや！ハハッ、ゴメンゴメン！！",
                                500)

                        args = [type("Context", (), {
                                    "guild": guild, "author": member,
                                    "name": item["name"]
                                }),
                                self.pop_main(item)]
                        if (cog := self.cogs.get(command_name)):
                            args = [cog] + args
                        create_task(data["callback"](*args))
            else:
                raise exceptions.SanicException("そのサーバーっているんですかぁ？", 404)
        else:
            raise exceptions.SanicException("ログインしてね。", 403)


def setup(bot):
    bot.add_cog(SettingManager(bot))
