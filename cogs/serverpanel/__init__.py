from os import listdir
import traceback


async def setup(bot):
    await bot.load_extension("cogs.serverpanel._oldrole")
    for name in listdir("cogs/serverpanel"):
        if not name.startswith(("_", ".")):
            try:
                await bot.load_extension(
                    f"cogs.serverpanel.{name[:-3] if name.endswith('.py') else name}")
            except Exception:
                traceback.print_exc()
            else:
                bot.print("[Extension]", "Loaded", name)  # ロードログの出力
