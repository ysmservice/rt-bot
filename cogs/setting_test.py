# RT - Setting API Test

from discord.ext import commands

from rtutil import SettingManager


class SettingTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def setting_callback(self, ctx, mode, items):
        if mode == "read":
            for item in items:
                if item == "text:item_1":
                    yield {"text": "現在書き込まれているデータ",
                           "multiple_line": False}
                elif item == "check:item_2":
                    yield {"checked": False}
                elif item == "radios:item_3":
                    yield {"1": True, "2": False}
                elif item == "list:item_4":
                    yield {"index": 0, "texts": ["野獣先輩", "SZ姉貴", "SZK兄貴"]}
        else:
            print("これを書き込めと言われました。:", items)

    @commands.command()
    @SettingManager.setting(
        "guild", "setting_guild_test",
        {"ja": "設定テストguild", "en": "Setting Test guild"},
        ["administrator"], setting_callback,
        {"text:item_1": {"ja": "日本語のテキストボックス名", "en": "English Text Box Name"},
         "check:item_2": {"ja": "日本語のチェックボックス名", "en": "English Check Box Name"},
         "radios:item_3": {"ja": "日本語のラジオボタン名", "en": "English Radio Button Name"},
         "list:item_4": {"ja": "日本語のリストボックス名", "en": "English List Button Name"}}
    )
    async def setting_test(self, ctx):
        await self.setting_callback(ctx, "write", {})

    @commands.command()
    @SettingManager.setting(
        "user", "setting_user_test",
        {"ja": "設定テストguild", "en": "Setting Test guild"}, [], setting_callback,
        {"text:item_1": {"ja": "日本語のテキストボックス名", "en": "English Text Box Name"},
         "check:item_2": {"ja": "日本語のチェックボックス名", "en": "English Check Box Name"},
         "radios:item_3": {"ja": "日本語のラジオボタン名", "en": "English Radio Button Name"},
         "list:item_4": {"ja": "日本語のリストボックス名", "en": "English List Button Name"}}
    )
    async def setting_test_user(self, ctx):
        await self.setting_callback(ctx, "write", {})


def setup(bot):
    bot.add_cog(SettingTest(bot))
