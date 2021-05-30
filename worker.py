# RT - Worker Program

import rtutil


worker = rtutil.Worker("r2!")


@worker.command()
async def test(ws, data, ctx, mode: int):
    print(data["content"])
    # r2!test 1
    print(type(mode), mode)
    # -> <class 'int'> 1


worker.run()
