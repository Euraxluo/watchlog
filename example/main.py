import asyncio

from watchlog.watchlog import start

loop = asyncio.get_event_loop()
loop.run_until_complete(start('config.json'))
