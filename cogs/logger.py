# RT落ちの情報収集ためのロガー

import discord
from discord.ext import commands, tasks
import collections
import logging

class SystemLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.names = []
        self.zero_parents = []
        self.authors = []
        self.guilds = []

    @tasks.loop(seconds=60)
    async def logging_loop(self):
        if len(names) == 0:return
        name = collections.Counter(self.names).most_common()[0]
        zero_parent = collections.Counter(self.zero_parents).most_common()[0]
        author = collections.Counter(self.authors).most_common()[0]
        guild = collections.Counter(self.guilds).most_common()[0]
        e = discord.Embed(title="RT command log", description=f"この1分間で{len(self.names)}回のコマンド実行がありました。")
        e.add_field(name="最も多く実行されたコマンド", value=f"{name[0]}：{name[1]}回")
        e.add_field(name="最も多く実行されたコマンド(Group)", value=f"{zero_parent[0]}：{zero_parent[1]}回")
        e.add_field(name="最も多くのコマンドを実行したユーザー", value=f"{self.bot.get_user(author[0])}({author[0]})：{author[1]}回")
        e.add_field(name="最も多くのコマンドが実行されたサーバー", value=f"{self.bot.get_guild(guild[0]).name}({guild[0]})：{guild[1]}回")
        await self.bot.get_channel(926731137903104000).send(embed=e)

    @commands.command()
    @commands.is_owner()
    async def command_logs(self, ctx):
        if len(names) == 0:return
        name = collections.Counter(self.names).most_common()[0]
        zero_parent = collections.Counter(self.zero_parents).most_common()[0]
        author = collections.Counter(self.authors).most_common()[0]
        guild = collections.Counter(self.guilds).most_common()[0]
        e = discord.Embed(title="RT command log", description=f"この1分間で{len(self.names)}回のコマンド実行がありました。")
        e.add_field(name="最も多く実行されたコマンド", value=f"{name[0]}：{name[1]}回")
        e.add_field(name="最も多く実行されたコマンド(Group)", value=f"{zero_parent[0]}：{zero_parent[1]}回")
        e.add_field(name="最も多くのコマンドを実行したユーザー", value=f"{self.bot.get_user(author[0])}({author[0]})：{author[1]}回")
        e.add_field(name="最も多くのコマンドが実行されたサーバー", value=f"{self.bot.get_guild(guild[0]).name}({guild[0]})：{guild[1]}回")
        await ctx.reply(embed=e)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logging_loop.start()

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.names.append(ctx.command.name)
        self.zero_parents.append(ctx.command.name if len(ctx.command.parents) == 0 else ctx.command.parents[-1].name)
        self.authors.append(ctx.author.id)
        self.guilds.append(ctx.guild.id)

def setup(bot):

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        filename='log/discord.log', encoding='utf-8', mode='w',
        maxBytes=10000000, backupCount=50
    )
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    bot.add_cog()
