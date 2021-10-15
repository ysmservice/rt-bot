# RT.AutoMod - Guild

from typing import TYPE_CHECKING, Optional, List, Dict

import discord

from ujson import loads, dumps
from functools import wraps
from time import time
from copy import copy

from .constants import DB, AM, MAX_INVITES, DEFAULT_LEVEL, DEFAULT_WR, DefaultWarn
from .modutils import similer, emoji_count

if TYPE_CHECKING:
    from aiomysql import Pool, Cursor
    from .__init__ import AutoMod
    from .types import Data


class DataManager:
    """セーブデータを管理するためのクラスです。"""

    def __init__(self, cog: "AutoMod"):
        self.pool: "Pool" = cog.bot.mysql.pool
        self.cog = cog
        self.cog.bot.loop.create_task(self.prepare_table())

    async def prepare_table(self) -> None:
        """テーブルの作成とコグにAutoModが設定されているサーバーのIDのリストのキャッシュを作る。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {DB} (
                        GuildID BIGINT, Data JSON
                    );"""
                )

                await cursor.execute(f"SELECT GuildID FROM {DB};")
                for row in await cursor.fetchall():
                    if row:
                        self.cog.guild_cache.append(row[0])

    async def _exists(self, cursor: "Cursor", guild_id: int) -> bool:
        # 渡されたCursorを使って存在確認を行う。
        await cursor.execute(
            f"SELECT GuildID FROM {DB} WHERE GuildID = %s;",
            (guild_id,)
        )
        return bool(await cursor.fetchone())

    async def get_guild(self, guild_id: int) -> "Guild":
        """サーバーのAutoModの設定用クラスを取得します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert await self._exists(cursor, guild_id), "見つかりませんでした。"
                await cursor.execute(
                    f"SELECT Data FROM {DB} WHERE GuildID = %s;",
                    (guild_id,)
                )
                return Guild(
                    self.cog, self.cog.bot.get_guild(guild_id),
                    loads((await cursor.fetchone())[0])
                )

    async def setup(self, guild_id: int) -> "Guild":
        """サーバーのAutoModの設定を登録します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert not await self._exists(cursor, guild_id), "既に登録されています。"
                await cursor.execute(
                    f"INSERT INTO {DB} VALUES (%s, %s);",
                    (guild_id, r"{}")
                )
                return Guild(self.cog, self.cog.bot.get_guild(guild_id), {})

    async def setdown(self, guild_id: int) -> None:
        """サーバーのAutoModの設定を削除します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert await self._exists(cursor, guild_id), "設定が見つかりませんでした。"
                await cursor.execute(
                    f"DELETE FROM {DB} WHERE GuildID = %s;",
                    (guild_id,)
                )


def commit(func):
    # このデコレータをつけた関数は実行後にデータを更新します。
    @wraps(func)
    async def new(self: "Guild", *args, **kwargs):
        data = await func(self, *args, **kwargs)
        await self._commit()
        return data
    return new


class Guild:
    """サーバーのAutoModの設定の管理やモデレーションを行うクラスです。"""

    def __init__(
        self, cog: "AutoMod", guild: discord.Guild, data: "Data"
    ):
        self.pool: "Pool" = cog.bot.mysql.pool
        self.guild = guild
        self.cog = cog
        self.data: "Data" = data

        for key in ("warn",):
            if key not in self.data:
                self.data[key] = {}

        for base in ("warn",):
            before = copy(self.data[base])
            for key in before:
                del self.data[base][key]
                self.data[base][int(key)] = before[key]
        del before

    async def _commit(self) -> None:
        # 設定を更新する関数です。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"UPDATE {DB} SET Data = %s WHERE GuildID = %s;",
                    (dumps(self.data), self.guild.id)
                )

    def _check_warn(self, warn: float):
        # 警告数が適切が確かめます。
        assert 0 <= warn <= 100, "warnは3以上100以下である必要があります。"

    @commit
    async def set_warn(self, user_id: int, warn: float) -> None:
        """ユーザーに警告を設定します。
        warnが0以上100以下ではない場合は`AssertionError`が発生します。"""
        self._check_warn(warn)
        self.data["warn"][user_id] = warn

    @commit
    async def add_ignore(self, sid: int) -> None:
        """チャンネルIDまたは役職IDを例外リストに入れます。"""
        if "ignores" not in self.data:
            self.data["ignores"] = []
        assert sid not in self.data["ignores"], "それは例外リスト既に追加されています。"
        self.data["ignores"].append(sid)

    @commit
    async def remove_ignore(self, sid: int) -> None:
        """チャンネルIDまたは役職IDを例外リストから削除します。"""
        if "ignores" not in self.data:
            self.data["ignores"] = []
        assert sid in self.data["ignores"], "それは例外リストに追加されていません。"
        self.data["ignores"].remove(sid)

    @commit
    async def mute(self, warn: float, role_id: int) -> None:
        """ミュートをする警告数を設定します。
        warnが0以上100以下ではない場合は`AssertionError`が発生します。"""
        self._check_warn(warn)
        self.data["mute"] = (warn, role_id)

    @commit
    async def ban(self, warn: float) -> None:
        """BANをする警告数を設定します。
        warnが0以上100以下ではない場合は`AssertionError`が発生します。"""
        self._check_warn(warn)
        self.data["ban"] = warn

    @commit
    async def emoji(self, max_: int) -> None:
        """絵文字数規制を設定します。
        0以上4000以下でないと`AssertionError`が発生します。"""
        assert 4000 >= max_ >= 0, "max_は0以上である必要があります。"
        self.data["emoji"] = max_

    @commit
    async def add_invite_channel(self, channel_id: int) -> None:
        """招待リンク規制での招待リンク作成可能チャンネルを追加します。"""
        if "invites" not in self.data:
            self.data["invites"] = []
        assert len(self.data["invites"]) < MAX_INVITES, "追加しすぎです。"
        self.data["invites"].append(channel_id)

    @commit
    async def remove_invite_channel(self, channel_id: int) -> None:
        """招待リンク規制での招待リンク作成可能チャンネルを削除します。"""
        if "invites" not in self.data:
            self.data["invites"] = []
        self.data["invites"].remove(channel_id)

    @commit
    async def set_withdrawal(self, seconds: int) -> None:
        """即抜けを検知する範囲を設定します。
        5以上300以下でないとAssertionErrorが発生します。"""
        assert 5 <= seconds <= 300, "5以上300以下でないといけません。"
        self.data["withdrawal"] = seconds

    async def trial_invite(self, invite: discord.Invite) -> None:
        """招待が有効か確かめます。"""
        admin = False
        # invite.inviterはMemberオブジェクトではないので取得し直す。
        if (guild := self.cog.bot.get_guild(invite.guild.id)):
            if (member := guild.get_member(invite.inviter.id)):
                # サーバーの管理者かどうかをチェックする。
                admin = member.guild_permissions.administrator

        if (self.data.get("invite_filter", False) and not admin
            and invite.channel.id not in self.data.get("invites", ())):
            await invite.delete(
                reason=f"{AM}招待作成不可なチャンネルなため。"
            )
            try:
                await invite.inviter.send(
                    embed=discord.Embed(
                        title=DB,
                        description={
                            "ja": f"{invite.guild.name}の{invite.channel.name}では招待を作成することができません。",
                            "en": f"It is not possible to create an invitation link in the {invite.channel.name} of the {invite.guild.name}."
                        }, color=self.cog.COLORS["warn"]
                    )
                )
            except Exception as e:
                if self.cog.bot.test:
                    print("Error on TrialInvite:", e)

    @commit
    async def trigger_invite(self) -> bool:
        """招待リンク規制の有効/無効を切り替えます。"""
        self.data["invite_filter"] = not self.data.get("invite_filter", False)
        return self.data["invite_filter"]

    @property
    def invites(self) -> List[int]:
        """招待リンクを作ることができるチャンネルのIDのリストを取得します。
        もし招待リンク規制が有効になっていない場合は何があっても空のリストになります。"""
        if self.data.get("invite_filter", False):
            return self.data.get("invites", [])
        return []

    @commit
    async def level(self, level: int = DEFAULT_LEVEL) -> None:
        """サーバーのスパム検知レベルを設定します。
        設定されない場合は定数の`constants.DEFAULT_LEVEL`が使用されます。"""
        assert 1 <= level <= 100, "一以上百以下である必要があります。"
        self.data["level"] = level

    async def trial_message(self, message: discord.Message) -> None:
        """メッセージをスパムチェックします。"""

        if (not hasattr(message.author, "guild_permissions") or all(
            getattr(message.author.guild_permissions, name)
            for name in ("manage_roles", "ban_members")
        ) or (message.author.bot and message.author.public_flags.verified_bot)
        or message.author.discriminator == "0000"):
            # 管理者または認証済みのBotまたはwebhookならチェックをしない。
            return

        if any(
            message.author.get_role(id_) or message.channel.id == id_
            for id_ in self.data.get("ignores", ())
        ):
            # 例外設定に引っ掛かったら無視する。
            return

        warn = 0
        try:
            if "before" in self.cog.cache[message.channel.id][message.author.id]:
                assert similer(
                    self.cog.cache[message.channel.id] \
                        [message.author.id]["before"],
                    message.content
                )
                self.cog.cache[message.channel.id][message.author.id]["count"] = \
                    self.cog.cache[message.channel.id][message.author.id] \
                    .get("count", 0) + 1
            else:
                assert False
        except AssertionError:
            # もしスパムじゃないならカウントをリセットする。
            self.cog.cache[message.channel.id][message.author.id]["count"] = 0
        finally:
            self.cog.cache[message.channel.id][message.author.id]["time"] = time()
            self.cog.cache[message.channel.id][message.author.id]["before"] = \
                message.content

            if self.cog.cache[message.channel.id][message.author.id]["count"] \
                >= self.data.get("level", DEFAULT_LEVEL):
                # もしスパム検知レベルに達したのなら警告を一つ上げる。
                warn += 1

        if (e := emoji_count(message.content)) > self.data.get("emoji", 4000):
            # もし絵文字数制限にひっかかったのなら警告を一つ上げる。
            await message.channel.send(
                f"{message.author.mention}, このサーバーは絵文字数は`{self.data['emoji']}`が最大です。\n" \
                "絵文字の入れすぎに注意してください。"
            )
            warn += 0.5

        if 0 < warn <= 100:
            await self.set_warn(
                message.author.id, self.data.get("warn", {}).get(
                    message.author.id, 0
                ) + warn
            )
            await self.trial_user(message.author, message.channel.send)

    async def trial_user(
        self, member: discord.Member,
        send: Optional[discord.TextChannel.send] = None
    ) -> None:
        """ユーザーのwarnチェックをし必要なら処罰をします。"""
        if member.id in self.data.get("warn", {}) and (
            not member.guild_permissions.administrator
            or self.cog.bot.test
        ) and not (message.author.bot and message.author.public_flags.verified_bot):
            mute, role_id = self.data.get("mute", (DefaultWarn.MUTE, 0))
            ban = self.data.get("ban", DefaultWarn.BAN)

            try:
                if self.data["warn"][member.id] >= ban:
                    # もしBANするほど警告数が溜まったらBANする。
                    await member.ban(reason=f"{AM}スパムのため。")
                    assert False, f"1{member.mention}をスパムのためBANしました。"

                elif self.data["warn"][member.id] >= mute:
                    # もしミュートするほど警告数が溜まったらミュートする。
                    if "mute" in self.data:
                        assert (role := member.guild.get_role(role_id)), \
                            "0付与するロールが見つからないため"
                        if not member.get_role(role.id):
                            await member.add_roles(role, reason=f"{AM}スパムのため。")
                            assert False, f"1{member.mention}をスパムのためミュートにしました。"

                elif send and self.data["warn"][member.id] >= ban - 2:
                    # もしあと警告二回を食らったらBANになるなら警告をしておく。
                    await send(f"{member.mention}, これ以上スパムメッセージを送信するとBANされます。")

                elif send and self.data["warn"][member.id] >= mute // 2:
                    # もしあと半分でミュートになるのなら警告をしておく。
                    await send(f"{member.mention}, これ以上スパムメッセージを送信するとミュートになります。")

            except (AssertionError, discord.Forbidden) as e:
                e = "0権限がないため" if isinstance(e, discord.Forbidden) else str(e)
                await self.log(
                    ("**エラー！**\n"
                    f"{member.mention}をスパムで処罰しようと試みましたが、{e[1:]}処罰ができませんでした。"
                    if e[0] == "0" else e[1:]),
                    color=self.cog.COLORS["error" if e[0] == "0" else "warn"]
                )
                if send and e[0] == "1":
                    await send(e[1:])
                    await self.set_warn(member.id, 0)

    async def trial_member(self, member: discord.Member) -> None:
        """渡されたメンバーが即抜けを繰り返しているかどうかをチェックします。
        もし繰り返しているのなら設定されているBANをする。"""
        if member.id in self.cog.withdrawal_cache:
            if time() <= self.cog.withdrawal_cache[member.id]:
                # 処罰を執行する。
                del self.cog.withdrawal_cache[member.id]
                await self.log(f"{member.name}を即抜け後にすぐまた参加したためBANしました。")
                return await member.ban(reason=f"{AM}即抜けしたため。")
        self.cog.withdrawal_cache[member.id] = \
            time() + self.data.get("withdrawal", DEFAULT_WR)

    async def log(self, description: str, **kwargs) -> None:
        """ログを流します。"""
        kwargs["color"] = kwargs.get("color") or self.cog.COLORS["warn"]
        for channel in self.guild.text_channels:
            if getattr(channel, "topic", "") and "rt>modlog" in channel.topic:
                await channel.send(
                    content=f"<t:{int(time())}>",
                    embed=discord.Embed(
                        title=self.cog.__cog_name__,
                        description=description, **kwargs
                    )
                )
                break