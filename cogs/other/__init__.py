from os import listdir
import traceback


async def setup(bot):
    for name in listdir("cogs/other"):
        if not name.startswith(("_", ".")):
            try:
                await bot.load_extension(
                    f"cogs.other.{name[:-3] if name.endswith('.py') else name}")
            except Exception:
                traceback.print_exc()
            else:
                bot.print("[Extension]", "Loaded", name)  # ロードログの出力
