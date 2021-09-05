# RT - Channel Plugin

from discord.ext import commands
import discord

from re import findall


HELPS = {
    "ja": ("画像, URLの自動スポイラー", """# 画像, URLの自動スポイラー
これは`rt>asp`をチャンネルトピックに入れることでタイトル通り画像とURLにスポイラーがついてメッセージが再送信されるようになります。  
なお、`rt>asp`の他に単語を空白で分けて右に書けばその言葉もスポイラーするようになります。

### 警告
これを使うとスポイラーがついた際に再送信するのでメッセージを編集することができなくなります。

### メモ
`rt>ce`をチャンネルトピックに入れることで全部のメッセージが再送信されて編集できなくなります。  
(権限がない限りであって他の人のメッセージを削除することができる人はメッセージの削除が可能です。)  
失言を許さないサーバーオーナーは設定してみましょう。"""),
    "en": ("Image, URL Auto Spoiler", """# Automatic spoiler for images, URLs
This will resend the message with spoilers for images and URLs by putting `rt>asp` in the channel topic, as the title says.  
In addition to `rt>asp`, you can also spoil words by separating them with spaces and writing them on the right.

### Warning
If you use this, the message will be resent when it is spoiled and you will not be able to edit it.

### Notes.
If you put `rt>ce` in a channel topic, all messages will be resent and you will not be able to edit them.  
(You can delete messages if you are not authorized to do so and can delete other people's messages.""")
}


class ChannelPluginGeneral(commands.Cog):

    URL_PATTERN = "https?://[\\w/:%#\\$&\\?\\(\\)~\\.=\\+\\-]+"

    def __init__(self, bot):
        self.bot = bot
        for lang in HELPS:
            self.bot.cogs["DocHelp"].add_help(
                "ChannelPlugin", "ChannelPlugin",
                lang, HELPS[lang][0], HELPS[lang][1]
            )

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.Thread):
            return
        if not message.guild or message.author.bot:
            return

        if message.channel.topic:
            for cmd in message.channel.topic.splitlines():
                if cmd.startswith("rt>asp"):
                    # Auto Spoiler
                    content = message.clean_content
                    # 添付ファイルをスポイラーにする。
                    new = []
                    for attachment in message.attachments:
                        attachment.filename = f"SPOILER_{attachment.filename}"
                        new.append(await attachment.to_file())
                    # urlをスポイラーにする。
                    for url in findall(self.URL_PATTERN, content):
                        content = content.replace(url, f"||{url}||", 1)
                    # もしスポイラーワードが設定されているならそれもスポイラーにする。
                    for word in cmd.split()[1:]:
                        content = content.replace(word, f"||{word}||")
                    if message.clean_content != content or message.attachments:
                        # 送信しなおす。
                        await message.channel.webhook_send(
                            content, files=new,
                            username=message.author.display_name,
                            avatar_url=message.author.avatar.url
                        )
                        await message.delete()
                elif cmd.startswith("rt>ce"):
                    # Can't Edit
                    await message.channel.webhook_send(
                        message.clean_content, files=[
                            await at.to_file()
                            for at in message.attachments
                        ], username=message.author.display_name,
                        avatar_url=message.author.avatar.url
                    )
                    await message.delete()


def setup(bot):
    bot.add_cog(ChannelPluginGeneral(bot))