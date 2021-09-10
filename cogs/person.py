# RT - Person

from discord.ext import commands
import discord

from typing import Optional, List, Tuple

from aiohttp import ClientSession
from datetime import timedelta
from bs4 import BeautifulSoup
import asyncio


class Person(commands.Cog):

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'
    }
    YAHOO_ICON = "http://tasuren.syanari.com/RT/yahoo_favicon.PNG"
    QUESTIONS = ("とは", "とは?", "とは？", "って何", "って何？",
                 "って何?", "ってなに", "ってなに？", "ってなに?")
    EMOJIS = {
        "UserFlags.hypesquad_bravery": "<:HypeSquad_Bravery:876337861572579350>",
        "UserFlags.hypesquad_brilliance": "<:HypeSquad_Brilliance:876337861643882506>",
        "UserFlags.hypesquad_balance": "<:HypeSquad_Balance:876337714679676968>",
        "search": "<:search:876360747440017439>"
    }

    def __init__(self, bot):
        self.bot = bot
        self.session = ClientSession()

    async def search_message(
        self, channel: discord.TextChannel, original: discord.Message,
        content: str, **kwargs
    ) -> Optional[discord.Message]:
        async for message in channel.history(**kwargs):
            if message.id != original.id and content in message.clean_content:
                return message

    @commands.command(
        extras={
            "headding": {
                "ja": "指定したメッセージに指定した絵文字を付与します。",
                "en": "Auto Reaction"
            }, "parent": "Individual"
        }, aliases=["ar", "自動反応", "おーとりあくしょん"]
    )
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def autoreaction(self, ctx, message_content, *, emojis, message = None):
        """!lang ja
        --------
        自動で指定されたメッセージに指定された絵文字のリアクションを付与します。

        Parameters
        ----------
        message_content : str
            リアクションをつけるメッセージにある文字列です。  
            ここを`ch`または`channel`にした場合はチャンネルに設定されて、そのチャンネルに送ったメッセージ全部にその絵文字がつくようになります。  
            これをオフにする際はチャンネルトピックにある`rt>ar`から始まる行を削除することでオフにできます。
        emojis : str
            絵文字です。

        Examples
        --------
        `rt!autoreaction how 👍 👎`

        Aliases
        -------
        ar, 自動反応, おーとりあくしょん

        !lang en
        --------
        Automatically adds the specified pictogram reaction to the specified message.

        Parameters
        ----------
        message_content : str
            The string in the message to be reacted.
        emojis : str
            Emojis.

        Examples
        --------
        `rt!autoreaction how 👍 👎`

        Aliases
        -------
        ar"""
        if message_content in ("ch", "channel"):
            await ctx.channel.edit(
                topic="rt>ar " + emojis
            )
            await ctx.reply("Ok")
        else:
            message = message or await self.search_message(
                ctx.channel, ctx.message, message_content
            )
            if message:
                if not message:
                    await ctx.trigger_typing()

                errors, pass_count, did = "", 0, 0
                for emoji in emojis:
                    did += 1
                    if pass_count:
                        pass_count -= 1
                    elif emoji not in (" ", "　", "\n", ":"):
                        if emoji == "<":
                            emoji = emojis[did:emojis.find(">") + 1]
                            pass_count = len(emoji)
                        try:
                            await message.add_reaction(emoji)
                        except discord.HTTPException:
                            errors += f"\n{emoji}を付与することができませんでした。"

                if not message:
                    await ctx.reply(f"Ok{errors}")
            else:
                await ctx.reply(
                    {"ja": "そのメッセージが見つかりませんでした。",
                    "en": "That message is not found."}
                )

    @commands.command(
        extras={
            "headding": {"ja": "指定されたユーザーIDまたはユーザー名からユーザー情報を取得します。",
                         "en": "Search user by id or name."},
            "parent": "Individual"
        },
        aliases=["ui", "search_user", "ゆーざーいんふぉ！", "<-これかわいい！"]
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(self, ctx, *, user_name_id = None):
        """!lang ja
        --------
        指定されたユーザーの名前またはユーザーIDからユーザー情報を取得します。

        Notes
        -----
        ユーザー名の場合はRTが入っている何かしらのサーバーにいるユーザーでないと取得はできません。

        Parameters
        ----------
        user : ユーザーIDまたはユーザー名
            見たいユーザー情報のユーザーのIDまたは名前です。

        Aliases
        -------
        ui, search_user, ゆーざーいんふぉ！, <-これかわいい！

        Examples
        --------
        `rt!userinfo tasuren`

        !lang en
        --------
        Search user.

        Notes
        -----
        In the case of a user name, you need to be a user on some kind of server that contains RT to get it.

        Parameters
        ----------
        user : User ID or Name
            Target user id or name.

        Aliases
        -------
        ui, search_user

        Examples
        --------
        `rt!userinfo tasuren`"""
        await ctx.trigger_typing()
        # もしuser_name_idが指定されなかった場合は実行者のIDにする。
        if user_name_id is None:
            user_name_id = ctx.author.id
        # ユーザーオブジェクトを取得する。
        try:
            user_id = int(user_name_id)
            user = None
        except ValueError:
            for guild in self.bot.guilds:
                user = discord.utils.get(guild.members, name=user_name_id)
                break
            member = discord.utils.get(ctx.guild.members, name=user_name_id)
        else:
            user = await self.bot.fetch_user(user_id)
            member = ctx.guild.get_member(user_id)

        if user:
            # ユーザー情報のEmbedを作る。
            embeds = []
            bot = (f" **`{'✅' if user.public_flags.verified_bot else ''}BOT`**"
                   if user.bot else "")
            embed = discord.Embed(
                title=f"{user}{bot}",
                description="".join(
                    self.EMOJIS.get(str(flag), "")
                    for flag in user.public_flags.all()
                ) if user.public_flags else "",
                color=self.bot.colors["normal"]
            )
            embed.set_thumbnail(url=user.avatar.url)
            embed.add_field(name="ID", value=f"`{user.id}`")
            embed.add_field(
                name={
                    "ja": "Discord登録日時",
                    "en": "..."
                },
                value=(user.created_at + timedelta(hours=9)
                ).strftime('%Y-%m-%d %H:%M:%S')
            )
            embeds.append(embed)
            # サーバーのユーザー情報のEmbedを作る。
            if member:
                embed = discord.Embed(
                    title={
                        "ja": "このサーバーでの情報",
                        "en": "..."
                    },
                    description=(
                        "@everyone, "+ ", ".join(
                        role.mention for role in member.roles
                        if role.name != "@everyone")
                    ),
                    color=member.color
                )
                embed.add_field(
                    name={"ja": "表示名",
                          "en": "..."},
                    value=member.display_name
                )
                embed.add_field(
                    name={"ja": "参加日時",
                          "en": "..."},
                    value=(member.joined_at + timedelta(hours=9)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                )
                if member.voice:
                    embed.add_field(
                        name={"ja": "接続中のボイスチャンネル",
                            "en": "..."},
                        value=f"<#{member.voice.channel.id}>"
                    )
                embeds.append(embed)
            # 作ったEmbedを送信する。
            for embed in embeds:
                await ctx.send(embed=embed)
            del embeds, embed
        else:
            # 見つからないならエラーを発生させる。
            raise commands.errors.UserNotFound(
                "そのユーザーの情報が見つかりませんでした。"
            )

    async def yahoo(self, keyword: str) -> Tuple[str, List[Tuple[str, str]]]:
        # yahooで検索を行います。
        results = []
        url = 'https://search.yahoo.co.jp/search?p=' + \
            keyword.replace(" ", "+").replace("　", "+")

        async with self.session.get(url, headers=self.HEADERS) as r:
            html = await r.text()

        soup = BeautifulSoup(html, "html.parser")
        soup = soup.find_all("section")
        for d in soup:
            k = d.find("h3")
            if k:
                k = k.find("span")
                d = d.find("a")
                results.append(
                    (getattr(k, "text", None),
                     d.get("href") if d else None)
                )

        return url, [k for k in results[1:] if k[1] is not None]

    async def search(self, word: str, max_: int = 5) -> Optional[discord.Embed]:
        # self.yahooを使ってYahooで検索をした結果をEmbedにします。
        result = await self.yahoo(word)
        if result:
            url, result = result
            length = len(result)
            embed = discord.Embed(
                title={"ja": f"{word}の検索結果",
                       "en": f"{word}..."},
                description="\n".join(
                    f"[{result[i][0]}]({result[i][1]})"
                    for i in range(max_ if length > max_ else length)
                ),
                color=0xfd4d70, url=url
            )
            embed.set_footer(
                text={"ja": "Yahoo 検索",
                      "en": "Yahoo Search"},
                icon_url=self.YAHOO_ICON
            )
            del url, length, result
            return embed
        return None

    @commands.command(
        extras={
            "headding": {"ja": "Yahooで検索をします。",
                         "en": "..."},
            "parent": "Individual"
        },
        name="yahoo",
        aliases=["search", "yho", "ahoo", "やふー！"]
    )
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def yahoo_(self, ctx, *, word):
        """!lang ja
        --------
        Yahooで検索をします。

        Notes
        -----
        8秒に一回実行することができます。

        Parameters
        ----------
        word : str
            検索ワードです。

        Aliases
        -------
        search yho, ahoo, やふー！

        !lang en
        --------
        ..."""
        await ctx.trigger_typing()
        if (embed := await self.search(word)):
            await ctx.reply(embed=embed)
        else:
            await ctx.reply({"ja": "見つかりませんでした。",
                             "en": "..."})

    def cog_unload(self, loop=None):
        if loop is None:
            loop = self.bot.loop
        if loop and self.session is not None:
            loop.create_task(self.session.close())
            self.session = None

    @commands.Cog.listener()
    async def on_close(self, loop):
        self.cog_unload(loop=loop)

    @commands.Cog.listener()
    async def on_message(self, message):
        if (not message.guild or not hasattr(message.channel, "topic")
                or not message.channel.topic or message.author.bot):
            return

        # 自動リアクション
        for line in message.channel.topic.splitlines():
            if line.startswith("rt>ar "):
                await self.autoreaction(
                    await self.bot.get_context(message),
                    "", emojis=line[6:], message=message
                )

        # もし`OOOとは。`に当てはまるなら押したら検索を行うリアクションを付ける。
        for question in self.QUESTIONS:
            if message.content.endswith(question):
                word = message.content[:0 - len(question)]

                if word:
                    await message.add_reaction(self.EMOJIS["search"])
                    try:
                        reaction, user = await self.bot.wait_for(
                            'reaction_add', timeout=5.0,
                            check=lambda reaction, user: (
                                str(reaction.emoji) == self.EMOJIS["search"]
                                and user.id == message.author.id
                            )
                        )
                    except asyncio.TimeoutError:
                        # もしリアクションが押されないならリアクションを削除する。
                        try:
                            await message.remove_reaction(
                                self.EMOJIS["search"], self.bot.user)
                        except (discord.HTTPException, discord.Forbidden,
                                discord.NotFound, discord.InvalidArgument):
                            pass
                    else:
                        # もしリアクションが押されたならコマンドを実行する。
                        await self.yahoo_(await self.bot.get_context(message), word=word)
                return

        if isinstance(message.channel, discord.Thread):
            return

        # もしtopicにrt>searchがあるならメッセージを検索する。
        if (message.guild and message.channel.topic
                and "rt>search" in message.channel.topic):
            await self.yahoo_(await self.bot.get_context(message), word=message.content)


def setup(bot):
    bot.add_cog(Person(bot))
