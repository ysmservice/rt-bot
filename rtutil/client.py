
# RT - Shard

import discord
from discord.ext import commands

from traceback import format_exc
from os import cpu_count
import asyncio


TITLES = {
    "wp": "RT - Worker Pool",
    "wt": "RT - Worker Task",
    "rt": "RT - Client"
}


class RTShardClient(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        # 独自のkwargsを取得しておく。
        self.worker_count = kwargs.get("worker_count", cpu_count())
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
        # Prefix
        self.prefix = tuple(self.command_prefix)

        # Workerの作成する。
        self._print("wt", "Setting now!")
        self.queue = asyncio.Queue()

        for i in range(self.worker_count):
            name = "RT-Worker-" + str(i)
            self.loop.create_task(self.worker(name), name=name)
            self._print("wt", f"Setting worker {name}...")
        self._print("wt", "Done!")

        self.add_event(self.process_commands)

    async def worker(self, name: str):
        # Worker
        while True:
            current_queue = await self.queue.get()
            # Botがcloseしたならループを抜ける。
            if self.is_closed():
                break
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                if len(current_queue) == 2:
                    event_type, args = current_queue
                    kwargs = {}
                elif len(current_queue) == 3:
                    event_type, args, kwargs = current_queue
                # イベントを走らせるがもしエラーがおきたらエラー時の関数を呼び出す。
                try:
                    await self.run_event(event_type, args, kwargs)
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

    async def run_event(self, event_type: str, args: list = [],
                        kwargs: dict = {}):
        # 登録されたイベントを呼び出す。
        if event_type == "not_event":
            await args[0](*args[1:], **kwargs)
        coros = self.events.get(event_type)
        if coros:
            for coro in coros:
                await coro(*args, **kwargs)

    async def add_queue(self, coro, args: list = [], kwargs: dict = {}):
        await self.queue.put(["not_event", [coro] + args, kwargs])

    async def run_command(self, message):
        await self.queue.put(["process_commands", [message]])

    async def on_message(self, message):
        await self.run_command(message)

    def add_event(self, coro, cname=None):
        # イベントの登録デコレータ。
        if asyncio.iscoroutinefunction(coro):
            name = coro.__name__
        else:
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        if cname:
            name = cname
        # イベントを登録する。
        if name in self.events:
            self.events[name].append(coro)
        else:
            self.events[name] = [coro]
        self._print("rt", f"Event {coro.__name__} registered.")

        return coro

    def remove_event(self, coro, cname=None):
        # イベントの登録解除デコレータ。
        # もしコルーチンじゃなかったらTypeErrorを発生させる。
        if asyncio.iscoroutinefunction(coro):
            cname = coro.__name__
        else:
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        if cname:
            name = cname
        # イベントの登録を解除する。
        if name in self.events:
            del self.events[name][self.events[name].index(coro)]
            if not self.events[name]:
                self.events[name]
            self._print("rt", "Event removed.")
        else:
            raise TypeError("そのイベントはまだ登録されていません。")
