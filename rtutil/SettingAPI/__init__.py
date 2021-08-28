# rtutil - Setting API

from discord.ext import commands
import discord

from .classes import (SettingData, SettingItem, TextBox,
	 				  CheckBox, ListBox, RadioButton, Context,
                      SettingType, ModeType, get_bylang)
from . import utils

from sanic import exceptions, response
from typing import Type, List
from data import get_headers
from functools import wraps
from rtlib import OAuth


def login_require(coro):
    # ログインしていないならSanicExceptionを発生するデコレータです。
    @wraps(coro)
    async def new_coro(self, request, *args, **kwargs):
        if request.ctx.user:
            return response.json(
                await coro(self, request, *args, **kwargs),
                headers=get_headers(self.bot, request)
            )
        else:
            raise exceptions.SanicException(
                message="あなたは誰でしょうか？",
                status_code=403
            )
    return new_coro


class SettingAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {"guild": {}, "user": {}}

    @commands.Cog.listener()
    async def on_command_add(self, command: Type[commands.Command]):
        # コマンドに設定が設定されているなら設定リストに登録する。
        if command.extras and (data := command.extras.get("setting")):
            self.data[data.setting_type][command.qualified_name] = {
                "command": command,
                "data": data
            }

    @commands.Cog.listener()
    async def on_command_remove(self, command: Type[commands.Command]):
        # コマンドが削除されたかつそのコマンドに設定が設定されているなら設定を削除する。
        if (command.extras and (data := command.extras.get("setting"))
                and command.qualified_name in self.data[data.setting_type]):
            del self.data[data.setting_type][command.qualified_name]

    @staticmethod
    def error(text: str, code: int = 500) -> None:
        raise exceptions.SanicException(message=text, status_code=code)

    def check_permissions(self, member: discord.Member,
                          permissions: List[str]) -> bool:
        # 権限を持っているか確認をする。
        return all(getattr(member.guild_permissions, permission_name)
                   for permission_name in permissions)

    async def get_commands(self, lang: str, setting_type: SettingType,
                     mode: ModeType, member: discord.Member) -> dict:
        # コマンドのデータを取得する。
        return {
            command_name: {
                "description": get_bylang(
                    self.data[setting_type][command_name]["data"].description,
                    lang
                ),
                "items": {
                    item.name: data
                    for item, data in await self.data \
                        [setting_type][command_name]["data"]
                        .get_dictionary(
                            self.data[setting_type][command_name]["command"]
                                .cog, lang, mode, member
                        )
                }
            }
            for command_name in self.data[setting_type]
            if (setting_type == "user"
                or self.check_permissions(
                    member,
                    self.data[setting_type][command_name]["data"].permissions
                ))
        }

    @commands.Cog.route("/api/settings/guild")
    @OAuth.login_want()
    @login_require
    async def setting_guild(self, request):
        return {
            "status": "ok", "settings": {
                str(guild.id): {
                    "name": guild.name, "icon": (
                        guild.icon.url if guild.icon
                        else None),
                    "commands": await self.get_commands(
                        self.bot.cogs["Language"].get(request.ctx.user),
                        "guild", "read", member
                    )
                }
                for guild in self.bot.guilds
                if (member := guild.get_member(request.ctx.user.id))
            }
        }

    @commands.Cog.route("/api/settings/user")
    @OAuth.login_want()
    @login_require
    async def setting_user(self, request):
        return {
            "status": "ok", "settings": await self.get_commands(
                self.bot.cogs["Language"].get(request.ctx.user),
                "user", "read", request.ctx.user
            )
        }

    async def update_setting(self, request, setting_type, member):
        for command_name, data in request.json.items():
            cmd_name, item_name = command_name.split(".")
            if setting_type == "user" or self.check_permissions(
                    member, self.data[setting_type][cmd_name]["data"]
                        .permissions
                    ):
                try:
                    await self.data[setting_type][cmd_name]["data"] \
                        .update_setting(
                            self.data[setting_type][cmd_name]["command"]
                                .cog, item_name, data, member
                        )
                except exceptions.SanicException as e:
                    return {
                        "status": "error",
                        "code": e.code,
                        "message": e.message
                    }
        return {"status": "ok"}

    @commands.Cog.route("api/settings/update/guild/<guild_id>", methods=["POST"])
    @OAuth.login_want()
    @login_require
    async def update_setting_guild(self, request, guild_id):
        if ((guild := self.bot.get_guild(int(guild_id)))
                and (member := guild.get_member(request.ctx.user.id))):
            return await self.update_setting(request, "guild", member)
        else:
            raise exceptions.SanicException(
                message="あなたが誰なのか私わからないの。ごめんなさい！",
                status_code=403
            )

    @commands.Cog.route("/api/settings/update/user", methods=["POST"])
    @OAuth.login_want()
    @login_require
    async def update_setting_user(self, request):
        return await self.update_setting(request, "user", request.ctx.user)


def setup(bot):
    bot.add_cog(SettingAPI(bot))