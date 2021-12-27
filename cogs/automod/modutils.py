# RT AUtoMod - Mod Utils

from typing import TYPE_CHECKING, Union, Any, List

import discord

from emoji import emoji_lis
from re import findall
from time import time

if TYPE_CHECKING:
    from .data_manager import GuildData
    from .cache import Cache


def similar(before: str, after: str, level: int = 15) -> float:
    "文章が似ているかチェックします。"
    length = len(after)
    if length < level:
        level = length
    return sum(
        any(after[i:i+level_child] in before for level_child in range(level))
        for i in range(level) if i+level <= length
    ) / length * 100


def join(message: discord.Message) -> List[str]:
    "渡されたメッセージにある文字列を全て合体させます。"
    contents = [message.content or ""]
    for embed in message.embeds:
        contents.append(
            "".join(map(lambda x: getattr(embed, x), ("title", "description")))
            + embed.footer.text
        )
    for attachment in message.attachments:
        contents.append(attachment.filename)
    return contents


def emoji_count(text: str) -> int:
    "渡された文字列にある絵文字の数を数えます。"
    return len(findall("<a?:.+:\d+>", text)) \
        + len([char for char in text if emoji_lis(char)])


async def log(
    cache: Union["Cache", discord.Member, Any], reason: str, subject: str
) -> discord.Message:
    "ログを流します。"
    for channel in cache.guild.text_channels:
        if channel.topic and "rt>automod" in channel.topic:
            return await channel.send(
                f"{cache.member.mention}を{reason}のため{subject}しました。"
            )


def get(cache: "Cache", data: "GuildData", key: str) -> Any:
    "GuildDataから特定のデータを抜き取ります。これはデフォルトをサポートします。"
    return data.get(key, cache.cog.DEFAULTS.get(key))


async def trial_message(self: "Cache", data: "GuildData") -> None:
    "渡されたUserData(Cache)のユーザーとメッセージを調べ、処罰すべきか裁判をし、処罰が必要な場合は相応の罰を下します。"
    if self.warn >= get(self, data, "ban"):
        await self.member.ban(reason=f"[AutoMod] スパムのため")
        await log(self, "スパム", "BAN")
    elif self.warn >= get(self, data, "mute"):
        # ToDo: Pycordのスラッシュへの移行作業後にTimeoutをここに実装する。
        await log(self, "スパム", "タイムアウト(未実装)")


def process_check_message(
    self: "Cache", data: "GuildData", message: discord.Message
) -> None:
    "渡されたメッセージをスパムかどうかをチェックします。"
    # もし以前送信したメッセージが不明な場合はチェックしない。
    if self.update_cache(message) is not None:
        # もし0.5秒以内に投稿されたメッセージなら問答無用でスパム認定とする。
        if self.checked <= time() + 0.5:
            self.suspicious += 50
        else:
            # 絵文字カウントをチェックします。
            if data["emoji"] < emoji_count(message.content):
                self.suspicious += 50
            # 以前送られたメッセージと似ているかをチェックし似ている度を怪しさにカウントします。
            self.suspicious += sum(
                similar(self.before_content, content) for content in join(message)
            )
        if self.process_suspicious():
            self.cog.bot.loop.create_task(trial_message(self, data))
    # もし招待リンク削除が有効かつ招待リンクがあるなら削除を行う。
    if "invite_deleter" in data:
        if findall(
            r"(https?:\/\/)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com\/invite)\/.+[a-z]",
            message.content
        ) and all(word not in message.content for word in data["invite_deleter"]):
            self.cog.bot.loop.create_task(discord.utils.async_all(
                (
                    message.author.send(
                        f"その招待リンクを{message.guild.name}に送信することはできません。"
                    ), message.delete()
                )
            ))


async def trial_new_member(self: "Cache", data: "GuildData") -> None:
    "渡された新規参加者のメンバーを即抜け等をしていないか調べて必要に応じて処罰をします。"
    if self.before_join is not None and "bolt" in data:
        if time() - self.before_join <= data["bolt"]:
            await self.member.ban(reason=f"[AutoMod] 即抜けのため")
            await log(self, "即抜け", "BAN")


async def trial_invite(data: "GuildData", invite: discord.Invite) -> None:
    "招待リンク規制対象かどうかをチェックして必要なら招待の削除を行います。"
    if hasattr(invite.guild, "get_member"):
        # もしinvite.guildがdiscord.Guildじゃなかったのならちゃんとしたのを取得する。
        if (guild := invite._state._get_guild(invite.guild.id)):
            invite.guild = guild
        else:
            # もしどこのサーバーかわからなかったのなら諦める。
            return
    # discord.Inviteのinviterはdiscord.Memberではないので取得し直す。
    if (member := invite.guild.get_member(invite.inviter.id)):
        # 管理者権限を持っている場合は例外とする。
        if member.guild_permissions.administrator:
            return
    if "invites" in data:
        if not any(
            member.get_role(id_) or invite.channel.id == id_
            for id_ in data["invites"]
        ):
            # もし例外対象じゃないのなら招待リンクを削除する。
            await invite.delete(reason=f"[AutoMod] 招待リンク作成不可なため")
            await member.send(
                f"{member.guild.name}の{invite.channel.name}では招待リンクを作ることができません。"
            )