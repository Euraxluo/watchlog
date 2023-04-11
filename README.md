
# watchlog

`watchlog` is a Python package for monitoring log files and sending parsed logs to a specified URL using HTTP POST requests.

- name = "watchlog"
- description = "monitoring log files and sending parsed logs to a specified URL"
- authors = ["Euraxluo <euraxluo@outlook.com>"]
- license = "The MIT LICENSE"
- repository = "https://github.com/Euraxluo/watchlog"
- version = "0.1.*"



## Installation

You can install `watchlog` using pip:

```bash
pip install watchlog
```

## Usage

To use `watchlog`, you need to create a configuration file in JSON format. Here is an example configuration file:

```json
{
  "files": [
    {
      "path": "/path/to/log/file.log",
      "reg": "^(?P<time>[^ ]*) (?P<level>[^ ]*) (?P<module>[^ ]*) (?P<line>[^ ]*) (?P<message>.*)$",
      "url": "http://example.com/api/logs",
      "latest": true,
      "headers": {
        "Content-Type": "application/json"
      },
      "auth": {
        "username": "user",
        "password": "pass"
      }
    }
  ]
}
```

- `path`: The path of the log file to monitor.
- `reg`: A regular expression used to parse the log file.
- `url`: The URL to send the parsed logs to.
- `latest`: Start monitoring from the latest logs.
- `headers`: A dictionary of headers to include in the HTTP POST request.
- `auth`: A dictionary with `username` and `password` keys for basic authentication.

Once you have created the configuration file, you can start monitoring the log file by calling the `start()` function from the `watchlog` module:

```python
import asyncio
from watchlog import start
loop = asyncio.get_event_loop()
loop.run_until_complete(start('path/to/config.json'))
```

You can also use we provide small scripts
```bash
watchlog path/to/config/file
```

This will start monitoring the log file specified in the configuration file and sending parsed logs to the specified URL using HTTP POST requests.

## example
example use zinc_observe as log search_engine,Illustrates the use of the process

```
.                     
├── __init__.py       
├── config.json             config file
├── docker-compose.yml      log search engine service
├── log.log                 log file
└── main.py                 main python file to monitor log file
```


## License

`watchlog` is licensed under the MIT license.