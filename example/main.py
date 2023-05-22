import asyncio

from watchlog.watchlog import start

loop = asyncio.get_event_loop()
import os

# 获取主文件所在的绝对路径
main_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(main_dir, "./config.json")
loop.run_until_complete(start(config_file))