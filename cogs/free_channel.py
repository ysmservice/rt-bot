# RT - Free Channel

from discord.ext import commands
import discord


class FreeChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        extras={
            "headding": {
                "ja": "実行したチャンネルをフリーチャンネル作成専用のチャンネルにします。",
                "en": "..."
            },
            "parent": "ServerPanel"
        },
        aliases=["fc", "FreeChannel", "自由チャンネル", "114514チャンネル"]
    )
    async def freechannel(self, ctx, lang="ja"):
        """!lang ja
        --------
        実行したチャンネルをフリーチャンネル作成専用のチャンネルにします。  
        このコマンドを実行したチャンネルに`text:チャンネル名`と送るとチャンネルが作られる感じです。  
        ボイスチャンネルの場合は`voice:チャンネル名`にすれば良いです。  

        Warnings
        --------
        このコマンドを実行できるのは`チャンネル管理`権限を持っている人のみです。  
        また作成されるフリーチャンネルはこのコマンドを実行したチャンネルのカテゴリー内です。  
        よってこのコマンドはカテゴリーの中にあるチャンネルでのみ実行可能です。
        
        Parameters
        ----------
        max_channel : int, default 4
            個人個人が作れる最大チャンネル数です。  
            入力しない場合は4となります。
        lang : str, default ja
            フリーチャンネルの説明のパネルを日本語か英語どっちで表示するかです。  
            入力しない場合は`ja`で日本語になっており英語にしたい場合は`en`にしてください。"""
        if ctx.channel.category is None:
            await ctx.reply(
                {"ja": "カテゴリーのあるチャンネルでのみこのコマンドは実行可能です。",
                 "en": "..."}
            )

        await ctx.trigger_typing()

        title = {"ja": "フリーチャンネル", "en": "Free Channel"}
        description = {
            "ja": """好きなチャンネル名を送信することでそのチャンネルを作成することができます。
**#** 作成方法
テキストチャンネル：`make text チャンネル名`
ボイスチャンネル：`make voice チャンネル名`
**#** 削除方法
テキストチャンネル：`remove text チャンネル名`
ボイスチャンネル：`remove voice チャンネル名`
※作成されるボイスチャンネルの名前には作成した人のIDが含まれますが、このIDは削除時にチャンネル名に入れる必要はないです。""",
            "en": "..."
        }

        footer = {"ja": f"一人{max_channel}個までチャンネルを作成可能です。",
                  "en": f"{max_channel}..."}
        embed = discord.Embed(
            title=title[lang],
            description=description[lang],
            color=self.bot.colors["normal"]
        )
        embed.set_footer(text=footer[lang])

        await ctx.channel.edit(
            topic=(f"RTフリーチャンネル\n作成可能チャンネル数：{max_channel}"
                   + "\nこのトピックは消さないでください。/ 英語版をここに")
        )
        await ctx.webhook_send(
            username=ctx.author.display_name, avatar=ctx.author.avatar.url,
            embed=embed
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        topic = message.channel.topic if message.channel.topic else ""
        if "RTフリーチャンネル" in topic and message.channel.category:
            if (message.author.id == self.bot.user.id
                    and ">," not in message.content):
                await message.delete()

            if message.author.bot:
                return
            else:
                await message.channel.trigger_typing()

            max_channel = int(topic[22:topic.find("\nこ")])
            user_id = str(message.author.id)
            now = {
                "text": [channel
                         for channel in message.channel.category.text_channels
                         if channel.topic and user_id in channel.topic],
                "voice": [channel
                          for channel in message.channel.category.voice_channels
                          if channel.name.endswith("-" + user_id)]
            }

            if ((message.content.startswith("make text ")
                    and len(now["text"]) < max_channel)
                    and (message.content.startswith("make voice")
                        and len(now["voice"]) < max_channel)):
                # チャンネルの作成。
                if str(message.channel.type) == "text":
                    coro = message.channel.category.create_text_channel(
                        message.content[10:], topic=f"RTフリーチャンネル, 作成者：{user_id}"
                    )
                    mode = ("テキスト", "text")
                else:
                    coro = message.channel.category.create_voice_channel(
                        "".join((message.content[11:], "-", user_id))
                    )
                    mode = ("ボイス", "voice")

                await coro
                await message.channel.send(
                    {"ja": f"{message.author.mention}, {mode[0]}チャンネルを作成しました。",
                     "en": f"{message.author.mention}, {mode[1]}..."},
                    delete_after=5
                )
            elif (message.content.startswith("remove text ")
                    or message.content.startswith("remove voice ")):
                # チャンネルの削除。
                # 削除ができるかチェックするcheckとmodeはtypeでiはコマンドから名前を取る際に使うインデックス番号。
                check, mode, i = (
                    (lambda ch: user_id in ch.topic, "text", 12)
                     if "text" in message.content
                     else
                    (lambda ch: ch.name.endswith(user_id),"voice", 13)
                )
                channel_name = message.content[i:]
                del i

                # 一つづつ取り出して名前が一致するかつ上のcheckがTrueになるやつを探す。
                for channel in data[mode]:
                    if channel.type == discord.ChannelType.voice:
                        name = channel.name[:channel.name.rfind("-")]
                    elif not channel.topic:
                        continue
                    else:
                        name = channel.name

                    if name == channel_name and check(channel):
                        # チャンネルを削除する。
                        await channel.delete()
                        await message.channel.send(
                            {"ja": f"{message.author.mention}, そのチャンネルを削除しました。",
                             "en": f"{message.author.mention}, ..."},
                            delete_after=5
                        )
                        break


def setup(bot):
    bot.add_cog(FreeChannel(bot))