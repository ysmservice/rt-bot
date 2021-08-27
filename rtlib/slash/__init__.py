# rtlib - Slash Command

from discord.ext import commands
import discord

from .types import (
    ApplicationCommand as ApplicationCommandType, OptionType
)
from .application_command import ApplicationCommand
from typing import Type, List, Dict

from .executor import executor
from inspect import signature
from .option import Option
from copy import copy


Route = discord.http.Route


class SlashCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # discord.pyが用意している簡単にリクエストをするためのもの。
        self.request = self.bot.http.request
        # 現在Discordに登録されているコマンド生のデータのリストです。
        self.now_commands: List[ApplicationCommandType] = []
        # スラッシュコマンドのコマンドを入れるためのリストです。
        self.commands: Dict[int, ApplicationCommand] = {}
        # queue
        self.queue: List[Type[commands.Command]] = []

    def check_list_same(
            self, former: dict, latter: dict,
            ignore: List[str], defaults: dict) -> bool:
        # 渡された二つのリストが同じかどうかを調べます。
        for data in former:
            dictionary = isinstance(data, dict)
            is_list = isinstance(data, list)
            for latter_data in latter:
                if dictionary and isinstance(latter_data, dict):
                    if self.check_dictionary_same(
                            data, latter_data, ignore, defaults):
                        break
                elif is_list and isinstance(latter_dat, dict):
                    if self.check_list_same(
                            data, latter_data, ignore, defaults):
                        break
                else:
                    if data == latter_data:
                        break
            else:
                return False
        return True

    def check_dictionary_same(
            self, former: dict, latter: dict, ignore: List[str],
            defaults: dict
        ) -> bool:
        # 渡された二つの辞書が同じかどうかを調べます。
        for key in former:
            if key not in ignore:
                if isinstance(former[key], dict):
                    if isinstance((latter_cache := latter.get(key)), dict):
                        if not self.check_dictionary_same(
                            former[key], latter_cache, ignore, defaults
                            ):
                            return False
                    else:
                        return False
                elif isinstance(former[key], list):
                    if isinstance((latter_cache := latter.get(key)), list):
                        if not self.check_list_same(
                            former[key], latter_cache, ignore, defaults
                            ):
                            return False
                    else:
                        return False
                elif former[key] != latter.get(key, defaults.get(key, None)):
                    return False
        return True

    def _get_data_from_command(
            self, command: Type[commands.Command], id_: int = None,
            option_mode: bool = False) -> dict:
        # コマンドのデータを作成します。
        data = {
            "name": command.name,
            "description": (command.description
                            if command.description
                            else "...")
        }
        if id_:
            data["id"] = id_

        # もしoptionの中身を作るために呼ばれたわけではないならtypeを割り当てておく。
        if not option_mode:
            target = command.root_parent or command
            data["application_id"] = str(self.bot.user.id)
            if "slash_command" in target.__original_kwargs__:
                data["type"] = 1
            elif "user_command" in target.__original_kwargs__:
                data["type"] = 2
            elif "message_command" in target.__original_kwargs__:
                data["type"] = 3
            else:
                data["type"] = 1
            data["default_permission"] = True
        if (child_commands := getattr(command, "commands", None)):
            # グループならoptionsの中にコマンドが入るからまたこの関数を呼び出す。
            data["options"] = [
                self._get_data_from_command(
                    sub_command, option_mode=True)
                for sub_command in child_commands
            ]
            # もしoptionのために呼び出されたのならそのoptionに対応したtypeを設定する。
            if option_mode:
                data["type"] = 2
        else:
            # グループじゃないならコマンドならコマンドの引数の情報をoptionsに入れる。
            data["options"] = []
            for parameter in signature(command.callback).parameters.values():
                if parameter.name in ("self", "ctx"):
                    continue
                # もしOptionのインスタンスじゃないアノテーションならOptionのインスタンスを自動で作る。
                option = parameter.annotation
                if not isinstance(option, Option):
                    option = Option(
                        option, parameter.name, "...",
                        required=parameter.default == parameter.empty
                    )
                # データにOptionを追加していく。
                data["options"].append(
                    {
                        "type": option.type, "name": option.name,
                        "description": option.description
                    }
                )
                if option.required:
                    data["options"][-1]["required"] = option.required
                if option.choices:
                    data["options"][-1]["choices"] = [
                        {"name": name, "value": value}
                        for name, value in option.choices
                    ]
                # もし,*,の後の引数ならそこで終了する。
                if parameter.kind == parameter.KEYWORD_ONLY:
                    break
            # もしoptionのために呼び出されたのならそのoptionに対応したtypeを設定する。
            if option_mode:
                data["type"] = 1

        # もしoptionsが空なら削除する。
        if not data["options"]:
            del data["options"]

        return data

    async def _update_commands(
            self, commands: List[Type[commands.Command]]
        ) -> None:
        # コマンドのデータを作りアップデートが必要ならスラッシュコマンドが更新する。
        change_command = False

        for command in commands:
            data = self._get_data_from_command(command)
            update = False

            for already_command in self.now_commands:
                # 既に登録されているコマンドと違うコマンドがあるなら更新フラグを立てる。
                if already_command["name"] == command.name:
                    check_target = copy(already_command)
                    update = not self.check_dictionary_same(
                        check_target, data, ("id", "version"),
                        {"required": False, "options": []}
                    )
                    break
            else:
                # もしコマンドが登録されていないなら更新フラグを立てる。
                update = True

            # 更新フラグが立っているならスラッシュコマンドを登録する。
            if update:
                already_command: ApplicationCommandType = await self.request(
                    Route("POST", f"/applications/{self.bot.user.id}/commands"),
                    json=data
                )
            # コマンドにSlashCommandのインスタンスをコマンドにくっつける。
            command.application_command = ApplicationCommand(
                self.bot, command, already_command
            )
            self.commands[command.application_command.name] = command.application_command
            change_command = True
        if change_command:
            await self._update_now_commands()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            if interaction.data["name"] in self.commands:
                application = copy(self.commands[interaction.data["name"]])
                application.interaction = interaction

                # 登録済みのコマンドのApplicaitonCommandのコピーにオプションを設定する。
                # これを実行時に使う。
                mode = 0
                application.options = [
                    Option.from_dictionary(option)
                    for option in interaction.data.get("options", ())
                    if ((mode := 2) if option["type"] in (1, 2)
                        else False) or True
                ]

                await executor(
                    self.bot, application, application.command,
                    mode, application.options
                )

    async def _update_now_commands(self) -> None:
        self.now_commands = await self.request(
            Route("GET", f"/applications/{self.bot.user.id}/commands")
        )

    @commands.Cog.listener()
    async def on_ready(self, command=None):
        # 既に登録されているスラッシュコマンドを取得する。
        await self._update_now_commands()
        # Botに登録されているコマンドをすべて取得する。
        await self._update_commands(self.queue)

    @commands.Cog.listener()
    async def on_command_add(self, command: Type[commands.Command]):
        if any(word in command.__original_kwargs__
                for word in (
                    "slash_command", "user_command",
                    "message_command"
                )):
            self.queue.append(command)


def setup(bot):
    bot.add_cog(SlashCommand(bot))