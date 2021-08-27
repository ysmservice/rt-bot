# rtlib.slash - Command Executor

from discord.ext import commands
import discord

from typing import Type, List

from inspect import signature, isfunction, iscoroutinefunction
from .application_command import ApplicationCommand
from .option import Option
from .types import Context


async def executor(
        bot: Type[commands.Bot], application: ApplicationCommand,
        command: Type[commands.Command], type_: int,
        options: List[Option] = None
    ) -> None:
    if type_ == 2:
        # グループコマンドならコマンドをオプションの中から探し出しまたそれを実行する。
        print(options)
        option = options[0]
        return await executor(
            bot, application,
            discord.utils.get(command.commands, name=option.name),
            option.type, option.options
        )
    else:
        # グループコマンドじゃないならそれはコマンドのはず。
        # なので引数を用意してコマンドを実行する。
        # まずはContextを作る。
        ctx = Context(bot, application)

        # optionsの中に引数に設定されたものがあるからそれを取り出す。
        args = ([application.command.cog]
                if application.command.cog else [])
        args.append(ctx)
        state = bot._connection

        for parameter, option in zip(
                    signature(
                        command.callback
                    ).parameters.values(),
                    options
                ):
            # 型変換を行う。
            if parameter.annotation == discord.User:
                option.value = discord.User(
                    state=state, data=option.value
                )
            elif parameter.annotation == discord.Member:
                option.value = discord.Member(
                    data=option.value, guild=ctx.guild, state=state
                )
            elif parameter.annotation in (
                    discord.TextChannel, discord.VoiceChannel,
                    discord.Thread, discord.StageChannel,
                    discord.CategoryChannel):
                option.value = option.value
            elif isfunction(parameter.annotation):
                coro = parameter.annotation(option.value)
                if iscoroutinefunction(parameter.annotation):
                    option.value = await coro
                else:
                    option.value = coro
            args.append(option.value)

        # 取り出した引数を使ってコマンドを実行する。
        await command.callback(*args)