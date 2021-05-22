# RT - Shard

import discord

from threading import Thread
from queue import Queue, Empty
from traceback import format_exc
from os import cpu_count
import asyncio


TITLES = {
    "wt": "RT - Worker Thread",
    "rt": "RT - Client"
}


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, *args, **kwargs):
        # 独自のkwargsを取得しておく。
        self.worker_count = kwargs.get("worker_count", cpu_count() * 2 + 1)
        self.print_error = kwargs.get("print_error", True)

        # ログ出力を準備する。
        self._print = ((lambda title, text: print("[" + TITLES[title] + "]", text))
                        if kwargs.get("log", False)
                        else lambda title, text: (title, text))
        self._print("rt", "Now setting...")
        self._print("rt", "You can print some log by client._print().")

        self.events = {}
        super().__init__(*args, **kwargs)

        # Workerの作成する。
        self._print("wt", "Setting now!")
        self.workers = []
        self.queue = Queue()
        for i in range(self.worker_count):
            name = f"RT-Worker-{i}"
            self.workers.append(
                Thread(target=self.worker,
                        args=(name,),
                        name=name)
            )
            self.workers[-1].start()
            self._print("wt", f"Setting worker {i}...")
        self._print("wt", "Done!")

        self.add_event_hook()

    # Workerにデータを転送するためのイベントを登録するやつ。
    def add_event_hook(self):
        @self.event
        async def on_ready():
            self._print("rt", "Connected!")
            self.queue.put(["on_ready", []])

        @self.event
        async def on_message(message):
            self.queue.put(["on_message", [message]])

        def on_reaction(reaction, user, event_type):
            self.queue.put(["on_reaction_" + event_type, [reaction, user]])

        @self.event
        async def on_reaction_add(reaction, user):
            on_reaction(reaction, user, "add")

        @self.event
        async def on_reaction_remove(reaction, user):
            on_reaction(reaction, user, "remove")

    def worker(self, name):
        # Worker
        while True:
            try:
                current_queue = self.queue.get_nowait()
            except Empty:
                current_queue = None
            # Botがcloseしたならループを抜ける。
            if self.is_closed():
                break
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                event_type, data = current_queue
                if event_type == "on_message":
                    if data[0].content == "r2!close":
                        self.loop.create_task(self.close())
                        break
                # イベントを走らせるがもしエラーがおきたらエラー時の関数を呼び出す。
                try:
                    self.run_event(event_type, data)
                except Exception as error:
                    self.on_worker_error(error, name)
                self.queue.task_done()
        self._print("wt", f"Thread {name} closed.")

    def on_worker_error(self, error, thread_name):
        # エラー時に呼び出される関数。
        formated_exc = f"Exception in thread {thread_name}:\n{format_exc()}"
        if self.print_error:
            print(formated_exc)
        else:
            self._print("wt", formated_exc)
        self.run_event(
            "on_worker_error",
            [error, formated_exc],
            kwargs={"thread_name": thread_name}
        )

    def run_event(self, event_type: str, data: list = [], kwargs: dict = {}):
        # 登録されたイベントを呼び出す。
        coros = self.events.get(event_type)
        if coros:
            for coro in coros:
                self.loop.create_task(coro(*data, **kwargs))

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

    def __del__(self):
        if not self.is_closed():
            self.close()
