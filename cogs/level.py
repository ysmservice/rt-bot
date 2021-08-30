# RT - Level

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseLocker
from rtlib.ext import Embeds
from typing import Tuple


class DataManager(DatabaseLocker):
    def __init__(self, db):
        self.db: mysql.MySQLManager = db
        self.auto_cursor = True

    async def init_table(self) -> None:
        await self.cursor.create_table(
            "level", {
                "GuildID": "BIGINT", "UserID": "BIGINT",
                "Exp": "INTEGER", "Level": "INTEGER"
            }
        )
        await self.cursor.create_table(
            "levelReward", {
                "GuildID": "BIGINT", "Level": "INTEGER",
                "Role": "BIGINT", "ReplaceRole": "BIGINT"
            }
        )
        await self.cursor.create_table(
            "levelNotification", {
                "UserID": "BIGINT", "Bool": "TINYINT"
            }
        )

    async def set_notification(self, user_id: int, onoff: bool) -> None:
        target = {"UserID": user_id}
        change = {"Bool": int(onoff)}
        if await self.cursor.exists("levelNotification", target):
            await self.cursor.update_data("levelNotification", change, target)
        else:
            target.update(change)
            await self.cursor.insert_data("levelNotification", target)

    async def get_notification(self, user_id: int) -> bool:
        target = {"UserID": user_id}
        if await self.cursor.exists("levelNotification", target):
            if (row := await self.cursor.get_data(
                    "levelNotification", target)):
                return bool(row[1])
            else:
                return True
        else:
            return True

    async def set_level(
            self, guild_id: int, user_id: int,
            exp: int, level: int
        ) -> None:
        target = {"GuildID": guild_id, "UserID": user_id}
        change = {"Exp": exp, "Level": level}
        if await self.cursor.exists("level", target):
            await self.cursor.update_data("level", change, target)
        else:
            target.update(change)
            await self.cursor.insert_data("level", target)

    async def get_level(self, guild_id: int, user_id: int) -> tuple:
        target = {"GuildID": guild_id, "UserID": user_id}
        if await self.cursor.exists("level", target):
            return await self.cursor.get_data("level", target)
        else:
            return (guild_id, user_id, 0, 0)

    async def get_levels(self, guild_id: int, limit: int = 10) -> tuple:
        await self.cursor.cursor.execute(
            """SELECT * FROM level
                WHERE GuildID = %s
                ORDER BY Level DESC
                LIMIT """ + str(limit),
            (guild_id,)
        )
        return await self.cursor.cursor.fetchall()

    async def set_reward(
            self, level: int, guild_id: int, role_id: int,
            replace_role_id: int = 0
        ) -> None:
        target = {"GuildID": guild_id, "Level": level}
        change = {"Role": role_id,
                  "ReplaceRole": replace_role_id}
        if await self.cursor.exists("levelReward", target):
            await self.cursor.update_data("levelReward", change, target)
        else:
            target.update(change)
            await self.cursor.insert_data("levelReward", target)

    async def delete_reward(self, guild_id: int, level:int) -> None:
        target = {"GuildID": guild_id, "Level": level}
        if await self.cursor.exists("levelReward", target):
            await self.cursor.delete("levelReward", target)
        else:
            raise KeyError("そのレベルは設定されていません。")

    async def get_reward(self, guild_id: int, level: int) -> tuple:
        target = {"GuildID": guild_id, "Level": level}
        if await self.cursor.exists("levelReward", target):
            return await self.cursor.get_data("levelReward", target)
        else:
            return ()


class Level(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()

    @commands.group(
        extras={
            "headding": {
                "ja": "Level機能, レベル報酬",
                "en": "Level, Level reward."
            }, "parent": "ServerUseful"
        }, aliases=["ll", "lv", "れべる", "レベル", "れべ"]
    )
    async def level(self, ctx):
        """!lang ja
        -------
        レベル機能です。  
        レベルは喋れば喋るほど上がります。  
        レベルには二種類ありグローバルレベルとローカルレベルがあります。  
        グローバルレベルは全サーバーが対象のレベルで、ローカルレベルはサーバー別のレベルでレベル報酬を設定することができます。  
        `rt!level`でランキングを見ることができます。

        Aliases
        -------
        ll, lv, れべる, レベル, れべ

        !lang en
        --------
        This is the level function.  
        The more you talk, the higher your level will be.  
        There are two types of levels: global level and local level.  
        The global level is for all servers, while the local level is for each server and allows you to set level rewards.  
        You can do `rt!level` to see level ranking.

        Aliases
        -------
        ll, lv"""
        if not ctx.invoked_subcommand:
            await ctx.trigger_typing()

            global_rows = await self.get_levels(0)
            local_rows = await self.get_levels(ctx.guild.id)
            global_row = await self.get_level(0, ctx.author.id)
            local_row = await self.get_level(ctx.guild.id, ctx.author.id)

            embeds = Embeds("LevelRanking", target=ctx.author.id)
            for mode, row, rows in (
                    (("グローバル", "Global"), global_row, global_rows),
                    ((ctx.guild.name, ctx.guild.name), local_row, local_rows)
                ):
                embeds.add_embed(
                    discord.Embed(
                        title={
                            "ja": f"レベルランキング - {mode[0]}",
                            "en": f"LevelRanking - {mode[1]}"
                        },
                        description="\n".join(
                            (f'{getattr(self.bot.get_user(row[1]), "name", "???")}'
                             f"：{row[3]}") for row in rows
                        ),
                        color=self.bot.colors["normal"]
                    ).add_field(
                        name="あなたのレベル",
                        value=f"Level: {row[3]}\nExp: {row[2]}"
                    )
                )
            await ctx.reply(embeds=embeds)

    @level.command(aliases=["notf", "nof", "通知"])
    async def notification(self, ctx, onoff: bool):
        """!lang ja
        -------
        レベルアップ時にレベルアップ通知用のリアクションをメッセージにつけるかどうかの設定コマンドです。

        Parameters
        ----------
        onoff : bool
            on/off

        Aliases
        -------
        notf, nof, 通知

        !lang ja
        -------
        This is the command to set whether or not to add a level-up notification reaction to the message when you level up.

        Parameters
        ----------
        onoff : bool
            on/off

        Aliases
        -------
        notf, nof"""
        await self.set_notification(ctx.author.id, onoff)
        await ctx.reply("Ok")

    @level.group(aliases=["rd", "報酬"])
    async def reward(self, ctx):
        """!lang ja
        --------
        レベル報酬機能です。  
        この機能を使うことによって百回喋った人のみに渡す役職などを設定でき、百回喋らないと宣伝チャンネルにメッセージを送信できないなどのことができます。

        Aliases
        -------
        rd, 報酬

        !lang en
        --------
        Level reward feature.  
        By using this function, you can set the position to be given only to the person who has spoken 100 times, and you can't send a message to the advertisement channel without speaking 100 times.

        Aliases
        -------
        rd"""
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    @reward.command("set")
    async def set_reward_(
            self, ctx, level: int, role: discord.Role,
            replace_role: discord.Role = None):
        """!lang ja
        --------
        報酬を設定します。  
        指定するレベルは[このレベルExp対応表](http://tasuren.syanari.com/RT/help/ServerUseful/level_table.png)を参考にして作るのを推奨します。  
        Expが喋った回数で例えば100Exp(100回喋った)の時が6レベルです。  
        なので百回喋った際に付与される役職を設定する場合は6をレベルに指定しましょう。

        Parameters
        ----------
        level : int
            役職を付与するトリガーとなるレベルです。
        role : 役職のメンションか名前
            levelの引数のレベルに達した際に付与する役職です。
        replace_role : 役職のメンションか名前, optional
            役職を付与する際に削除する役職で選択しなくても良いです。

        Examples
        --------
        `rt!level reward set 6 宣伝可能`  
        100回喋った人に宣伝可能という役職を付与するコマンドです。

        !lang en
        --------
        Set the reward.  
        It is recommended that you refer to the [This Level Exp Correspondence Table](http://tasuren.syanari.com/RT/help/ServerUseful/level_table.png) to make the level you specify.  
        Exp is the number of times you speak, for example, 100 exp (100 times you speak) is 6 levels.  
        So if you want to set a position that will be given to a player when he speaks 100 times, specify 6 as the level.

        Parameters
        ----------
        level : int
            The level that triggers the assignment of the role.
        role : mentor or name of the position
            The role to be assigned when the level of the level argument is reached.
        replace_role : mentor or name of the role, optional
            The role to be removed when granting the role.

        Examples
        --------
        `rt!level reward set 6 advertisable`.  
        This command assigns the position `advertisable' to a person who has spoken 100 times."""
        await self.set_reward(
            level, ctx.guild.id, role.id, getattr(replace_role, "id", 0)
        )
        await ctx.reply("Ok")

    @reward.command()
    async def reset(self, ctx, level: int):
        """!lang ja
        -------
        設定したレベル報酬を削除します。

        Parameters
        ----------
        level : int
            設定したレベル報酬のレベルです。

        !lang en
        --------
        Delete level reward setting.

        Parameters
        ----------
        level : int
            Target level."""
        try:
            await self.delete_reward(ctx.guild.id, level)
        except KeyError:
            await ctx.reply(
                {"ja": "そのレベルでは設定されていません。",
                 "en": "That level is not set."}
            )
        else:
            await ctx.reply("Ok")

    def level_calculation(self, exp: int, level: int) -> Tuple[bool]:
        exp += 1
        return exp, exp >= round((4 * (level ** 3)) / 5)

    async def role_error_wrap(self, coro) -> str:
        try:
            await coro
        except:
            return (
                "役職の位置がRTより下にあるか確認してください。"
                f"\nエラーコード：`{str(e)}`"
            )
        else:
            return ""

    async def on_levelup(
            self, level: int, guild_id: int,
            message: discord.Message) -> None:
        if await self.get_notification(message.author.id):
            # リアクションをつける。
            await message.add_reaction(
                ("<:level_up_global:876339471832997888>"
                 if guild_id
                 else "<:level_up_local:876339460252528710>")
            )

        if guild_id:
            # レベル報酬の付与をするところ。
            if (row := await self.get_reward(guild_id, level)):

                error_code = "役職が見つかりませんでした。"
                if (role := message.guild.get_role(row[2])):
                    if message.author.get_role(role.id):
                        error_code = ""
                    else:
                        error_code = await self.role_error_wrap(
                            message.author.add_roles(role)
                        )

                    if not error_code and row[3]:
                        error_code = "役職が見つかりませんでした。"
                        if (role := message.guild.get_role(row[3])):
                            if message.author.get_role(role.id):
                                error_code = await self.role_error_wrap(
                                    message.author.remove_roles(role)
                                )
                            else:
                                error_code = ""
                            print(role.name, error_code)

                if error_code:
                    await message.reply(
                        ("設定されているレベル役職を付与するのに失敗しました。"
                         f"\n{error_code}")
                    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.content.startswith(tuple(self.bot.command_prefix)):
            return

        for guild_id in (message.guild.id, 0):
            if (row := await self.get_level(guild_id, message.author.id)):
                level = row[3]
                exp, levelup = self.level_calculation(row[2], level)
                if levelup:
                    level += 1
                    await self.on_levelup(level, guild_id, message)

                await self.set_level(
                    guild_id, message.author.id, exp, level
                )


def setup(bot):
    bot.add_cog(Level(bot))