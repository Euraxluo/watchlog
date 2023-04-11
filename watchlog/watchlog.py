# -*- coding: utf-8 -*- 
# Time: 2023-04-11 10:57
# Copyright (c) 2023
# author: Euraxluo

import asyncio
import json
import os.path
from typing import List, Dict

import httpx
from loguru import logger
from watchdog.events import PatternMatchingEventHandler, FileSystemEventHandler
from watchdog.observers import Observer


class FileConfig:
    """
    Resolves the configuration file to log file monitoring configuration

    :param path:
    :param reg:
    :param url:
    :param headers:
    :param auth:
    :param latest:
    """

    def __init__(self, path, reg, url, headers, auth, latest=True):
        self.path: str = os.path.abspath(path)
        self.base_path: str = os.path.dirname(self.path)
        self.reg: str = reg
        self.url: str = url
        self.headers: Dict[str, str] = headers
        self.auth: httpx.BasicAuth = httpx.BasicAuth(auth['username'], auth['password'])
        self.latest: bool = latest

    def __repr__(self):
        return f'FileConfig(base_path={self.base_path}, path={self.path}, reg={self.reg}, url={self.url}, headers={self.headers}, auth={self.auth})'


class LogFileHandler(PatternMatchingEventHandler):
    def __init__(self, file_config: List[FileConfig]):
        """
        init log file handler, set the file path to be monitored, and set the offset of the file end
        :param file_config:
        """
        super().__init__(patterns=[fc.path for fc in file_config], ignore_directories=True)
        self.file_config = file_config
        self.config_map = {fc.path: fc for fc in file_config}
        self.offset_map = {fc.path: 0 for fc in file_config}
        for fc in file_config:
            if fc.latest:
                with open(fc.path, "rb") as f:
                    f.seek(0, 2)
                    self.offset_map[fc.path] = f.tell()

    @staticmethod
    async def send_log(log_data: List[Dict], url: str, headers: Dict, auth: httpx.BasicAuth):
        """
        Send log data to the specified url

        :param log_data:
        :param url:
        :param headers:
        :param auth:
        :return:
        """
        async with httpx.AsyncClient(auth=auth, headers=headers) as client:
            response = await client.post(url, json=log_data)
            if response.status_code == 200:
                print(f'Log sent success,response:{response.json()}')
            else:
                print(f'Failed to send log,response:{response.status_code} log:{log_data}')

    @staticmethod
    def cast(groups):
        for k, v in groups.items():
            if v.isdigit():
                groups[k] = int(v)

    def on_modified(self, event):
        """
        When the file is modified, the log is parsed and sent to the specified url

        :param event:
        :return:
        """
        config = self.config_map.get(event.src_path)
        if config is None:
            return
        try:
            with open(config.path, "r") as f:
                # Get the offset of the end of the file
                f.seek(0, 2)
                eof = f.tell()

                # Set the offset of the file to the last offset
                f.seek(self.offset_map[config.path])
                if f.tell() == eof:
                    return

                # Parse the log
                logs = list(logger.parse(f, config.reg, cast=self.cast))
                self.offset_map[config.path] = f.tell()

                # Send log
                if logs:
                    asyncio.run(self.send_log(logs, config.url, config.headers, config.auth))
                else:
                    print(f'No log found, file:{event.src_path}')

        except Exception as e:
            print(f'Failed to send log, error:{e} file:{event.src_path}')


def config_to_event_handler(file_path: str) -> Dict[str, FileSystemEventHandler]:
    """
    Read the configuration file and return the configuration list
    Convert the configuration file to a file monitoring event handler

    :param file_path:
    :return:
    """
    with open(file_path, 'r') as f:
        config = json.load(f)
        file_configs = [FileConfig(**i) for i in config['files']]
        base_config_map = {}
        for i in file_configs:
            if i.base_path not in base_config_map:
                base_config_map[i.base_path] = []
            base_config_map[i.base_path].append(i)
    event_handler_map = {}
    for path, file_configs in base_config_map.items():
        event_handler_map[path] = LogFileHandler(file_configs)
    return event_handler_map


async def start(config_file: str):
    observer = Observer()
    for base_path, handler in config_to_event_handler(config_file).items():
        observer.schedule(handler, path=base_path, recursive=False)
    observer.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def cli():
    import sys
    loop = asyncio.get_event_loop()
    if len(sys.argv)!=2:
        print("Useage: watchlog path/to/config.json")
        return
    loop.run_until_complete(start(sys.argv[1]))


__all__ = ["start", "cli"]
