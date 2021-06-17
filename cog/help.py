# RT - Help

from typing import Tuple, Callable
import rtutil, discord


CHECK_LIST = ("Parameters", "Returns", "Examples")
CATEGORIES = {
    "bot": "Bot関連",
    "server-tool": "サーバー(ツール)",
    "server-panel": "サーバー(パネル)",
    "server-safety": "サーバー(安全)",
    "server-useful": "サーバー(便利)",
    "individual": "個人",
    "entertainment": "娯楽",
    "chplugin": "チャンネルプラグイン",
    "mybot": "MyBot",
    "other": "その他"
}


class Help(metaclass=rtutil.Cog):
    def __init__(self, worker):
        self.worker = worker
        self.data = {}
        self.numbers = {}

    def parse(self, doc: str) -> Tuple[str, str, str]:
        """ドキュメンテーションを分けます。
        コマンドの関数についているドキュメンテーションをカテゴリーと見出しと説明に分解して返します。
        """
        splited = doc[:doc.find("\n")].split(",")
        category = splited[0] if splited else "その他"
        heading = splited[1] if len(splited) > 1 else ""
        description = doc.replace(category + "\n", "").replace(heading + "\n", "")
        new_description = ""
        for line in description.splitlines():
            if line.startswith("    "):
                e = 4
            elif line.startswith("  "):
                e = 2
            elif line.startswith("\t"):
                e = 1
            else:
                continue
            new_description += line[e:] + "\n"
        return category, heading, new_description[:-1]

    @rtutil.Cog.listener()
    def on_command_add(self, cmd):
        # コマンドのヘルプを取り出してヘルプに追加する。
        if cmd["coro"].__doc__:
            category, heading, description = self.parse(cmd["coro"].__doc__)
            if category not in self.data:
                self.data[category] = {}
            index = len(self.data[category]) + 1
            name = cmd["name"] + " " + heading
            self.numbers[index] = name
            self.data[category][index] = [name, description]
            print(self.data)

    @rtutil.Cog.listener()
    def on_command_remove(self, cmd):
        if cmd["doc"]:
            category, heading, _ = self.parse(cmd["doc"])
            name = cmd["name"] + " " + heading
            del self.data[category][self.numbers[name]]

    @rtutil.Cog.route("/help/<group_name>")
    async def help_web(self, data: dict, group_name: str):
        data = {"status": "ok", "title": None}
        if group_name in CATEGORIES:
            group_name = CATEGORIES[group_name]
            data["title"] = group_name
            data.update(self.data[group_name])
        else:
            data["status"] = "Not found"
        return self.worker.web("json", data)

    @rtutil.Cog.route("/help/<group_name>/<command_name>")
    async def help_web_detail(self, data: dict, group_name: str, command_name):
        data = {"status": "ok", "g-title": None, "content": None}
        if group_name in CATEGORIES:
            group_name = CATEGORIES[group_name]
            data["content"] = self.data[group_name][self.numbers[command_name]]
        else:
            data["status"] = "Not found"
        return self.worker.web("json", data)

    @rtutil.Cog.command()
    async def help(self, data, ctx):
        """Bot関連,Helpを表示します。
        Helpコマンドです。
        RTにあるコマンドを表示します。
        # 使用方法
        `rt!help`
        RTのコマンドリストのあるウェブサイトのURLを返します。

        `rt!help コマンド名`
        コマンド名のコマンドを表示します。
        コマンド名にカテゴリーの名前を入れると、そのカテゴリーのコマンドのリストを表示します。
        もし見つからない場合は検索されます。
        """
        embed = discord.Embed(
            title="ヘルプが必要ですか？",
            description="https://rt-bot.com/help.html\nでコマンドを確認することができます。",
            color=self.worker.colors["normal"]
        )
        await ctx.send(embed=embed)


def setup(worker):
    worker.add_cog(Help(worker))
