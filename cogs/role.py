# RT - Role Panel

from discord.ext import commands, tasks
import discord

from typing import Dict
from emoji import UNICODE_EMOJI_ENGLISH
from asyncio import create_task
from time import time


class RolePanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emojis = [chr(0x1f1e6 + i) for i in range(26)]
        self.queue: Dict[str, discord.RawReactionActionEvent] = {}
        self.worker.start()

    @commands.command(
        extras={"headding": {"ja": "役職パネルを作成します。", "en": "..."},
                "parent": "ServerPanel"}
    )
    @commands.has_permissions(administrator=True)
    async def role(self, ctx, title, *, content):
        """!lang ja
        --------
        役職パネルを作成します。  
        このコマンドは管理者権限を持っている人のみ実行が可能です。

        Parameters
        ----------
        title : str
            役職パネルのタイトルです。
        content : str
            改行で分けた役職パネルに入れる役職の名前またはメンション。  
            行の最初に絵文字を置くとその絵文字が役職パネルに使われます。  
            もし絵文字を置かない場合は自動で英文字の絵文字が割り振られます。

        Examples
        --------
        ```
        rt!role 遊んでいるゲーム
        Minecraft
        フォートナイト
        Geometry dash
        🥰 サノバウィッチ
        😘 ナルキッソス
        😊 闘神都市 II
        ```

        Notes
        -----
        🛠の絵文字を押すことでテンプレートを取得することができます。

        Raises
        ------
        400 Bad Request : 役職が見つからない際に発生します。

        !lang en
        --------
        上の説明の英語版をここに。"""
        emojis = self.parse_description(content, ctx.guild)
        if emojis:
            embed = discord.Embed(
                title=title,
                description="\n".join(f"{emoji} {emojis[emoji]}"
                                      for emoji in emojis),
                color=ctx.author.color
            )
            embed.set_footer(text="※連打防止のため役職の付与は数秒遅れます。")

            message = await ctx.webhook_send(
                "RT役職パネル", embed=embed, username=ctx.author.display_name,
                avatar_url=ctx.author.avatar.url, wait=True)
            await message.add_reaction("🛠")
            for emoji in emojis:
                await message.add_reaction(emoji)
        else:
            raise commands.errors.CommandError(
                "何も役職を指定されていないため役職パネルを作れません。")

    async def update_role(
            self, payload: discord.RawReactionActionEvent,
            emojis: Dict[str, str] = None) -> None:
        # 役職の付与剥奪を行う。
        # Embedから絵文字とメンションを取り出す。
        if emojis is None:
            emojis = self.parse_description(
                payload.message.embeds[0].description, payload.message.guild
            )
        key = str(payload.emoji)
        if key not in emojis:
            key = "<a" + key[1:]
        role = payload.message.guild.get_role(
            int(emojis[key][3:-1])
        )

        if role:
            # 役職が存在するならリアクションの付与と剥奪をする。

            if payload.event_type == "REACTION_ADD":
                await payload.member.add_roles(role)
            elif payload.event_type == "REACTION_REMOVE":
                await payload.member.remove_roles(role)

            del role
        else:
            try:
                await payload.member.send(
                    "".join(f"{payload.message.guild.name}での役職の付与に失敗しました。",
                            "\n付与する役職を見つけることができませんでした。"))
            except Exception as e:
                print(e)

    def parse_description(self, content: str, guild: discord.Guild) -> Dict[str, str]:
        # 文字列の行にある絵文字とその横にある文字列を取り出す関数です。
        i, emojis, result = -1, [], {}
        for line in content.splitlines():
            if line and line != "\n":
                i += 1
                not_mention: bool = "@" not in line

                if line[0] == "<" and all(char in line for char in (">", ":")):
                    if not_mention or line.count(">") != 1:
                        # もし外部絵文字なら。
                        emojis.append(line[:line.find(">") + 1])
                elif line[0] in UNICODE_EMOJI_ENGLISH or line[0] in self.emojis:
                    # もし普通の絵文字なら。
                    emojis.append(line[0])
                else:
                    # もし絵文字がないのなら作る。
                    emojis.append(self.emojis[i])
                    line = self.emojis[i] + " " + line

                result[emojis[-1]] = line.replace(emojis[-1], "")

                # もし取り出した役職名の最初が空白なら空白を削除する。
                if result[emojis[-1]][0] in (" ", "　"):
                    result[emojis[-1]] = result[emojis[-1]][1:]
                # もしメンションじゃないならメンションに変える。
                if not_mention:
                    role = discord.utils.get(guild.roles, name=result[emojis[-1]])
                    if role is None:
                        raise commands.errors.RoleNotFound(
                            f"{name}という役職が見つかりませんでした。")
                    else:
                        result[emojis[-1]] = role.mention

        return result

    def cog_unload(self):
        self.worker.cancel()

    @tasks.loop(seconds=4)
    async def worker(self):
        # キューにあるpayloadをupdate_roleに渡して役職の付与剥奪をする。
        # 連打された際に毎回役職を付与剥奪しないように。
        for cmid in list(self.queue.keys()):
            create_task(self.update_role(self.queue[cmid]))
            del self.queue[cmid]

    def check(self, payload: discord.RawReactionActionEvent) -> bool:
        # 役職パネルかチェックする。
        return (payload.message.embeds and payload.message.author.bot
                and payload.message.content == "RT役職パネル" and payload.message.guild
                and any(str(payload.emoji) == str(reaction.emoji)
                        or getattr(payload.emoji, "name", "") == \
                            getattr(reaction.emoji, "name", "fdslafsjkfjskaj")
                        for reaction in payload.message.reactions))

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload: discord.RawReactionActionEvent):
        if self.bot.is_ready():
            if self.check(payload):
                emoji = str(payload.emoji)
                # もしテンプレートの取得ならテンプレートを返す。
                if payload.event_type == "REACTION_ADD":
                    if emoji == "🛠":
                        emojis = self.parse_description(
                            payload.message.embeds[0].description,
                            payload.message.guild
                        )
                        await payload.member.send(
                            f"rt!role {payload.message.embeds[0].title}\n" + "\n".join(
                                (e + " " + getattr(
                                    payload.message.guild.get_role(int(m[3:-1])),
                                    "name", "役職が見つかりませんでした。")
                                ) for e, m in emojis.items()
                            )
                        )
                        return
                # キューに追加する。
                i = f"{payload.channel_id}.{payload.message_id}.{payload.member.id}"
                i += "." + emoji
                self.queue[i] = payload

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "🛠":
            await self.on_full_reaction_add(payload)


def setup(bot):
    bot.add_cog(RolePanel(bot))