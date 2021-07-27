# rtlib.libs - Support on_full_reaction_add/remove

from discord.ext import commands, tasks
import discord

from time import time
import asyncio


class OnFullReactionAddRemove(commands.Cog):
    """Backendで使うことのできる拡張コグの一つです。
    `on_raw_reaction_add/remove`と`on_reaction_add/remove`の合成版を作るためのコグ。
    `on_raw_reaction_add/remove`だとメッセージオブジェクトがないため毎回取得する必要がある。
    `on_reaction_add/remove`だとメッセージオブジェクトがあるが古いメッセージだと呼ばれない。
    これを両方使うのは非常にめんどくさいそしてrawに関しては毎回メッセージを取得する必要がある。
    これを解決するためのものがこのコグです。
    このコグは`rtlib.Backend.rtlibs`のリストに`on_full_reaction`の文字列を追加することで有効になる。
    このコグを有効にすると`on_full_reaction_add/remove`のイベントが使えるようになる。
    これは`discord.RawReactionActionEvent`にメッセージであるmessageを追加したものが引数で渡される。
    そしてadd/remove関係なくアクションをしたmemberが使用できます。"""
    def __init__(self, bot, timeout: float = 0.01):
        self.bot, self.timeout = bot, timeout
        self.cache, self.reactions = {}, {}
        self.cache_killer.start()

    def cog_unload(self):
        self.cache_killer.cancel()

    @tasks.loop(seconds=10)
    async def cache_killer(self):
        # 1分たったキャッシュは削除する。
        # キャッシュについては下の方の説明を読んでいけばわかる。
        try:
            now = time()
            delete_list = []
            for target, index, mode in ((self.cache, 1, "cache"),
                                        (self.reactions, 2, "reactions")):
                for key in target:
                    if target[key][index] < now:
                        delete_list.append((mode, key))
            for mode, key in delete_list:
                if mode == "cache":
                    del self.cache[key]
                elif mode == "reactions":
                    del self.reactions[key]
            del delete_list
        except Exception as e:
            print("Error on OnFullReactionAddRemove:", e)
            print("Please post issue about this error to github rtlib.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        asyncio.create_task(self.on_raw_reaction_addremove(payload, "add"))

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        asyncio.create_task(self.on_raw_reaction_addremove(payload, "remove"))

    def make_key(self, message_id: int, channel_id: int, guild_id: int,
                 emoji: discord.PartialEmoji, user_id: int, event: str) -> str:
        return f"{message_id}.{channel_id}.{guild_id}.{emoji}.{user_id}.{event}"

    @commands.Cog.listener()
    async def on_reaction_add(self, r, u):
        await self.on_reaction_addremove(r, u, "add")

    @commands.Cog.listener()
    async def on_reaction_remove(self, r, u):
        await self.on_reaction_addremove(r, u, "remove")

    async def on_reaction_addremove(self, reaction, user, event: str):
        # もし`on_reaction_add/remove`が呼ばれたら。
        # この説明を読む前に`self.on_raw_reaction_addremove`にある説明を1まで読もう。
        # ここでもしリアクションのデータと一緒に`asyncio.Event`があるなら、その`asyncio.Event.set`を実行する。
        # ここで見つからなかったら自分で作る。
        # `asyncio.Event.set`を実行した後は一緒に取得できたものを入れておく。
        key = self.make_key(reaction.message.id, reaction.message.channel.id,
                            reaction.message.guild.id if reaction.message.guild else 0,
                            reaction.emoji, user.id, event)
        if key in self.reactions:
            self.reactions[key][1] = [reaction, user]
        else:
            self.reactions[key] = [asyncio.Event(), [reaction, user], time()]
        self.reactions[key][0].set()

    async def on_raw_reaction_addremove(self, payload, event: str):
        # もしリアクションが付与または削除されたら。
        # `asyncio.Event`を渡されたリアクションのデータと一緒に保存する。
        # 大抵が`on_reaction_addremove`で先越されるのでそれはそっちに保存を任せる。
        # > ここまでを1とする。
        key = self.make_key(payload.message_id, payload.channel_id,
                            payload.guild_id if payload.guild_id else 0,
                            payload.emoji, payload.user_id, event)
        if key not in self.reactions:
            self.reactions[key] = [asyncio.Event(), [], time() + 3]

        # もし`self.on_reaction_addremove`の説明を読んでいないならそれを見よう。
        # `asyncio.Event.wait`でタイムアウトありで待つ。
        # もしリ`on_reaction_addremove`が呼ばれるならwaitはその時点で終わる。
        error = False
        try:
            await asyncio.wait_for(self.reactions[key][0].wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            # もし`self.on_reaction_addremove`が呼ばれなかった場合は自分でmessageを取得する。
            # この時キャッシュにmessageが既にあるならそのキャッシュを使用する。
            if (cache:=self.cache.get(payload.message_id)) is None:
                try:
                    channel = (self.bot.get_channel(payload.channel_id) if payload.guild_id
                               else self.bot.get_user(payload.user_id))
                    cache = [await channel.fetch_message(payload.message_id), time() + 60]
                    self.cache[payload.message_id] = cache
                    payload.member = (cache[0].guild.get_member(payload.user_id)
                                      if payload.guild_id else None)
                except Exception as e:
                    # なんらかの理由でメッセーいなどを取得できなかったら諦める。
                    error = True
            if not error:
                payload.message = cache[0]
        else:
            # もし`self.on_raction_addremove`が呼ばれたならそこからリアクションのデータをとる。
            reaction, user = self.reactions[key][1]
            payload.member = user
            payload.message = reaction.message
        finally:
            # `on_full_reaction_add/remove`を呼び出す。
            if not error:
                self.bot.dispatch("full_reaction_" + event, payload)


def setup(bot, *args, **kwargs):
    if "on_full_reaction_add/remove" in bot.rtlibs:
        bot.add_cog(OnFullReactionAddRemove(bot, *args, **kwargs))
