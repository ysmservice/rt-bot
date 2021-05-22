# RT - Shard

import discord

from traceback import format_exc
from os import cpu_count
import asyncio


TITLES = {
    "wp": "RT - Worker Pool",
    "wt": "RT - Worker Task",
    "rt": "RT - Client"
}


class RTShardClient(discord.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        # 独自のkwargsを取得しておく。
        self.worker_count = kwargs.get("worker_count", cpu_count() * 2 + 1)
        self.print_error = kwargs.get("print_error", True)
        self.print_log = kwargs.get("log", False)

        # ログ出力を準備する。
        self._print = ((lambda title, text: print(
                        "[" + TITLES[title] + "] " + text))
                       if self.print_log
                       else lambda title, text: (title, text))
        self._print("rt", "Now setting...")
        self._print("rt", "You can log using client._print().")

        self.events = {}
        super().__init__(*args, **kwargs)

        self.loop.run_until_complete(self.setup_worker())

    async def setup_worker(self):
        # Workerの作成する。
        self._print("wt", "Setting now!")
        self.queue = asyncio.Queue()

        for i in range(self.worker_count):
            name = "RT-Worker-" + str(i)
            self.loop.create_task(self.worker(name), name=name)
            self._print("wt", f"Setting worker {name}...")
        self._print("wt", "Done!")

        self.add_event_hook()

    async def worker(self, name: str):
        # Worker
        while True:
            current_queue = await self.queue.get()
            # Botがcloseしたならループを抜ける。
            if self.is_closed():
                break
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                event_type, data = current_queue
                # イベントを走らせるがもしエラーがおきたらエラー時の関数を呼び出す。
                try:
                    await self.run_event(event_type, data)
                except Exception as error:
                    await self.on_worker_error(error, name)
                self.queue.task_done()
        self._print("wt", f"Worker {name} closed.")

    async def on_worker_error(self, error, worker_name):
        # エラー時に呼び出される関数。
        formated_exc = f"Exception in worker {worker_name}:\n{format_exc()}"
        if self.print_error:
            print(formated_exc)
        else:
            self._print("wt", formated_exc)
        await self.run_event(
            "on_worker_error",
            [error, formated_exc],
            kwargs={"worker_name": worker_name}
        )

    async def run_event(self, event_type: str, data: list = [],
                        kwargs: dict = {}):
        # 登録されたイベントを呼び出す。
        coros = self.events.get(event_type)
        if coros:
            for coro in coros:
                await coro(*data, **kwargs)

    def add_event(self, coro):
        # イベントの登録デコレータ。
        # もしコルーチンじゃなかったらTypeErrorを発生させる。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        # イベントを登録する。
        if coro.__name__ in self.events:
            self.events[coro.__name__].append(coro)
        else:
            self.events[coro.__name__] = [coro]
        self._print("rt", f"Event {coro.__name__} registered.")

        return coro

    def remove_event(self, coro):
        # イベントの登録解除デコレータ。
        # もしコルーチンじゃなかったらTypeErrorを発生させる。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        # イベントの登録を解除する。
        if coro.__name__ in self.events:
            del self.events[coro.__name__]
            self._print("rt", "Event removed.")
        else:
            raise TypeError("そのイベントはまだ登録されていません。")

    # Workerにデータを転送するためのイベントを登録するやつ。
    def add_event_hook(self):
        @self.event
        async def on_ready():
            self._print("rt", "Connected!")
            await self.queue.put(["on_ready", []])

        @self.event
        async def on_message(message):
            await self.queue.put(["on_message", [message]])

        async def on_reaction(reaction, user, event_type):
            await self.queue.put(
                ["on_reaction_" + event_type, [reaction, user]])

        @self.event
        async def on_reaction_add(reaction, user):
            await on_reaction(reaction, user, "add")

        @self.event
        async def on_reaction_remove(reaction, user):
            await on_reaction(reaction, user, "remove")

        @self.event
        async def on_raw_reaction_add(payload, event_type="add"):
            await self.queue.put(["on_raw_reaction_" + event_type, [payload]])

        @self.event
        async def on_raw_reaction_remove(payload):
            await on_raw_reaction_add(payload, "remove")

        async def on_member(member, event_type):
            await self.queue.put(["on_member_" + event_type, [member]])

        @self.event
        async def on_member_join(member):
            await on_member(member, "join")

        @self.event
        async def on_member_remove(member):
            await on_member(member, "remove")

        @self.event
        async def on_raw_message_delete(payload):
            await self.queue.put(["on_raw_message_delete", [payload]])

        @self.event
        async def on_guild_channel_delete(channel, event_type="delete"):
            await self.queue.put(["on_guild_channel_" + event_type, [channel]])

        @self.event
        async def on_guild_channel_create(channel):
            await on_guild_channel_delete(channel, "create")

        @self.event
        async def on_guild_channel_update(before, after):
            await self.queue.put(["on_guild_channel_update", [before, after]])

        @self.event
        async def on_guild_update(before, after):
            await self.queue.put(["on_guild_update", [before, after]])

        @self.event
        async def on_guild_role_create(role, event_type="create"):
            await self.queue.put(["on_guild_role_" + event_type, [role]])

        @self.event
        async def on_guild_role_delete(role):
            await on_guild_role_create(role, "delete")

        @self.event
        async def on_guild_role_update(before, after):
            await self.queue.put(["on_guild_role_update", [before, after]])

        @self.event
        async def on_member_ban(guild, user, event_type="ban"):
            await self.queue.put(["on_member_" + event_type, [guild, user]])

        @self.event
        async def on_member_unban(guild, user):
            await on_member_ban(guild, user, "unban")

        @self.event
        async def on_invite_create(invite, event_type="create"):
            await self.queue.put(["on_invite_" + event_type, [invite]])

        @self.event
        async def on_invite_delete(invite):
            await on_invite_create(invite, "delete")
