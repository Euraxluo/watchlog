# -*- coding: utf-8 -*- 
# Time: 2023-04-11 10:57
# Copyright (c) 2023
# author: Euraxluo

import asyncio
import json
import os.path
from typing import List, Dict, TextIO, Union, Pattern

import httpx
import requests
from loguru import logger
from watchdog.events import PatternMatchingEventHandler, FileSystemEventHandler
from watchdog.observers import Observer

global CONFIG_FILE_PATH


class FileConfig:
    """
    Resolves the configuration file to log file monitoring configuration

    :param path:
    :param reg:
    :param url:
    :param headers:
    :param auth:
    :param enable:
    :param latest:
    """

    def __init__(self, path, reg, url, headers, auth, enable=True, latest=True):
        if os.path.isabs(path):
            self.path: str = os.path.abspath(path)
        else:
            self.path: str = os.path.join(os.path.dirname(os.path.abspath(CONFIG_FILE_PATH)), path)
            self.path = os.path.normpath(self.path)
        self.base_path: str = os.path.dirname(self.path)
        self.reg: str = reg
        self.url: str = url
        self.enable: bool = enable
        self.headers: Dict[str, str] = headers
        self.auth: httpx.BasicAuth = httpx.BasicAuth(auth['username'], auth['password'])
        self.latest: bool = latest

    def __repr__(self):
        return f'FileConfig(base_path={self.base_path}, path={self.path}, reg={self.reg}, url={self.url}, headers={self.headers}, auth={self.auth})'


class LogParse(object):
    @staticmethod
    def cast(groups):
        for k, v in groups.items():
            if v.isdigit():
                groups[k] = int(v)

    @staticmethod
    def parse(file: Union[str, TextIO], pattern: Union[str, Pattern[str]], ):
        return list(logger.parse(file, pattern, cast=LogParse.cast))


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

    def on_modified(self, event):
        """
        When the file is modified, the log is parsed and sent to the specified url

        :param event:
        :return:
        """
        print(f"parse {event.src_path}")
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
                logs = LogParse.parse(f, config.reg)
                self.offset_map[config.path] = f.tell()

                # Send log
                if logs:
                    asyncio.run(self.send_log(logs, config.url, config.headers, config.auth))
                else:
                    print(f'No log found, file:{event.src_path}')

        except Exception as e:
            print(f'Failed to send log, error:{e} file:{event.src_path}')


def config_to_file_config(config: dict) -> Dict[str, List[FileConfig]]:
    """
    Read the config and return the file configuration list

    :param config:
    :return:
    """
    base_config_map = {}
    file_configs = [FileConfig(**i) for i in config['files']]
    for fc in file_configs:
        if fc.enable is False:
            print(f"Config will be ignored:{fc.path}")
            continue
        errors = []
        try:
            # check the file path
            if not os.path.exists(fc.path):
                errors.append(f"path not exists :{fc.path}")
            # check the url
            requests.get(fc.url)
        except requests.exceptions.RequestException:
            errors.append(f"url not exists :{fc.url}")
        if errors:
            print(f"Config error at {fc}")
            for e in errors:
                print(e)
        if fc.base_path not in base_config_map:
            base_config_map[fc.base_path] = []
        base_config_map[fc.base_path].append(fc)
    return base_config_map


def config_to_event_handler(base_config_map: Dict[str, List[FileConfig]]) -> Dict[str, FileSystemEventHandler]:
    """
    Convert the configuration file to a file monitoring event handler

    :param base_config_map:
    :return:
    """
    event_handler_map = {}
    for path, file_configs in base_config_map.items():
        event_handler_map[path] = LogFileHandler(file_configs)
    return event_handler_map


async def start(config_file: str):
    ################################
    # 1. Check the configuration file
    ################################
    if not os.path.exists(config_file):
        print("Useage: watchlog path/to/config.json")
        return

    ################################
    # 2. Read the configuration file
    ################################
    config = {}
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print("Useage: watchlog path/to/config.json")
        print("watchlog error : ", e)
        return

    ################################
    # 3. Start the log file monitoring
    ################################
    global CONFIG_FILE_PATH
    CONFIG_FILE_PATH = config_file
    observer = Observer()
    for base_path, handler in config_to_event_handler(config_to_file_config(config)).items():
        print(f"observer monitor folder {base_path}")
        observer.schedule(handler, path=base_path, recursive=False)
    observer.start()
    ################################
    # 4. Start the config monitoring
    ################################
    if config.get("check", False):
        async def create_check_task():
            while True:
                await asyncio.sleep(config.get("check_interval", 5))

                print("========================")
                config_to_file_config(config)

        check_task = asyncio.create_task(create_check_task())  # 创建协程任务

    ################################
    # 5. Start the event loop
    ################################
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if config.get("log", False):
            check_task.cancel()
    observer.join()


def cli():
    import sys
    if len(sys.argv) == 2:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start(sys.argv[1]))
    if  len(sys.argv) == 4:
        if not os.path.exists(sys.argv[2]):
            print("Useage: watchlog --parse path/to/log_file pattern_str")
            return
        reg = sys.argv[3]
        print("json string pattern:")
        print(json.dumps(reg))
        print("input pattern:")
        print(reg)
        with open(sys.argv[2]) as l:
            print("log line:")
            print(l.readline())
            x = LogParse.parse(l, reg)
            print("parse result:")
            [print(i) for i in x]
    else:
        print("Useage:")
        print(" watchlog path/to/config.json")
        print(" watchlog --parse path/to/log_file pattern_str")
        return



__all__ = ["start", "cli", "LogParse"]
