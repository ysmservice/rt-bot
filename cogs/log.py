# RT - Log Extension
import datetime

import discord
from discord.ext import commands


def rl():
    return f"RTログ | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"


class Log(commands.Cog):
    def __init__(self, bot, data):
        self.bot, self.data = bot, data
        self.team_id = [667319675176091659,
                        634763612535390209, 693025129806037003]
        self.c = self.bot.colors["normal"]

    @commands.Cog.listener()
    async def on_member_join(self, member):
        for channel in member.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                bot = ""
                if member.bot:
                    bot = "<:bot:743378375321845791>"
                embed = discord.Embed(title="メンバーの参加", color=self.c)
                embed.add_field(name="名前", value=f"{member.mention}{bot}")
                embed.add_field(name="ユーザーID", value=str(member.id))
                embed.add_field(
                    name="Discord登録日", value=member.created_at.strftime('%Y-%m-%d'))
                embed.set_thumbnail(url=member.avatar_url_as(format="png"))
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        for channel in member.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                bot = ""
                if member.bot:
                    bot = "<:bot:743378375321845791>"
                embed = discord.Embed(title="メンバーの退出", color=self.c)
                embed.add_field(name="名前", value=f"{member.mention}{bot}")
                embed.add_field(name="ユーザーID", value=str(member.id))
                embed.set_thumbnail(url=member.avatar_url_as(format="png"))
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        cchannel = self.bot.get_channel(payload.channel_id)
        for channel in guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                if payload.cached_message is not None:
                    embed = discord.Embed(title="メッセージ削除", color=self.c)
                    embed.add_field(name="チャンネル", value=f"<#{cchannel.id}>")
                    embed.add_field(name="削除されたメッセージ",
                                    value=payload.cached_message.content)
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except BaseException:
                        pass
                else:
                    embed = discord.Embed(title="メッセージ削除", color=self.c)
                    embed.add_field(name="チャンネル", value=f"<#{cchannel.id}>")
                    embed.add_field(name="削除されたメッセージ",
                                    value="すいません！\n古すぎて取得できませんでした。")
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, nchannel):
        for channel in nchannel.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="チャンネルの削除", color=self.c)
                embed.add_field(name="チャンネル名", value=nchannel.name)
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, nchannel):
        for channel in nchannel.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="チャンネルの作成", color=self.c)
                embed.add_field(name="チャンネル名", value=nchannel.name)
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        for channel in after.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                if before.name != after.name:
                    embed = discord.Embed(title="チャンネル名の更新", color=self.c)
                    embed.add_field(name="更新前のチャンネル名", value=before.name)
                    embed.add_field(name="更新後のチャンネル名", value=after.name)
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        for channel in after.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                if before.name != after.name:
                    embed = discord.Embed(title="チャンネル名の更新", color=self.c)
                    embed.add_field(name="更新前のチャンネル名", value=before.name)
                    embed.add_field(name="更新後のチャンネル名", value=after.name)
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        for channel in role.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="役職の作成", color=self.c)
                embed.add_field(name="作成された役職", value=role.name)
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        for channel in role.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="役職の削除", color=self.c)
                embed.add_field(name="削除された役職", value=role.name)
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        for channel in after.guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                if before.name != after.name:
                    embed = discord.Embed(title="役職の更新", color=self.c)
                    embed.add_field(name="更新前の名前", value=before.name)
                    embed.add_field(name="更新後の名前", value=after.name)
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass

    @commands.Cog.listener()  # ko
    async def on_member_ban(self, guild, user):
        for channel in guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="ユーザーのBAN", color=self.c)
                embed.add_field(name="BANされたユーザー名", value=user)
                embed.add_field(name="BANされたユーザーID", value=user.id)
                embed.set_thumbnail(url=user.avatar_url_as(format="png"))
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        for channel in guild.text_channels:
            if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                embed = discord.Embed(title="ユーザーのBAN解除", color=self.c)
                embed.add_field(name="BAN解除されたユーザー名", value=user)
                embed.add_field(name="BAN解除されたユーザーID", value=user.id)
                embed.set_thumbnail(url=user.avatar_url_as(format="png"))
                embed.set_footer(text=rl())
                try:
                    await channel.send(embed=embed)
                except discord.errors.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild is not None:
            for channel in invite.guild.text_channels:
                if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                    bot = ""
                    if invite.inviter.bot:
                        bot = "<:bot:743378375321845791>"
                    embed = discord.Embed(
                        title="招待リンクの作成", description=f"{invite.inviter.mention}{bot} による実行", color=self.c)
                    embed.add_field(name="招待リンク", value=invite.url)
                    embed.set_thumbnail(
                        url=invite.inviter.avatar_url_as(format="png"))
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if invite.guild is not None:
            for channel in invite.guild.text_channels:
                if ("log-rt" in channel.name or 'rt>log' in (channel.topic if channel.topic else '')) and 'mlog-rt' not in channel.name:
                    embed = discord.Embed(title="招待リンクの削除", color=self.c)
                    embed.add_field(name="招待リンク", value=invite.url)
                    embed.set_footer(text=rl())
                    try:
                        await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        pass


def setup(bot):
    data = bot.data
    bot.add_cog(Log(bot, data))