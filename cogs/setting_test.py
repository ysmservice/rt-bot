# RT - Setting API Test

from discord.ext import commands

from rtutil.SettingAPI import *


class SettingTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def callback(self, ctx, item):
        print(ctx.mode, item.name, ctx.author.name,
              getattr(ctx.guild, "id", "サーバーはなし"))
        if ctx.mode == "write":
            print(item.text)
        return item

    @commands.command(
        extras={
            "setting": SettingData(
                "guild", {"ja": "テスト", "en": "test"}, callback,
                TextBox("item1", {"ja": "テキストボックス", "en": "textbox"}, "デフォルト"),
                RadioButton("item2", {"ja": "ラジオボタン", "en": "radio button"},
                            dict(radio1=True, radio2=False)),
                permissions=["administrator"]
            )
        }
    )
    async def _setting_api_test(self, ctx):
        pass

    @commands.command(
        extras={
            "setting": SettingData(
                "user", {"ja": "テスト", "en": "test"}, callback,
                TextBox("item1", {"ja": "テキストボックス", "en": "textbox"}, "デフォルト"),
                RadioButton("item2", {"ja": "ラジオボタン", "en": "radio button"},
                            dict(radio1=True, radio2=False))
            )
        }
    )
    async def _setting_api_test_user(self, ctx):
        pass


def setup(bot):
    bot.add_cog(SettingTest(bot))
