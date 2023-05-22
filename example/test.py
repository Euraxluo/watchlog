str = """
[2023-05-19 18:48:03.534]  INFO     [MainProcess,4790,MainThread,application,echo_routes] 43 : {'path': '/maps_algo/redoc', 'name': 'redoc_html', 'methods': {'GET', 'HEAD'}}
[2023-05-19 18:48:03.534]  INFO     [MainProcess,4790,MainThread,application,echo_routes] 43 : {'path': '/algo/simulation/', 'name': 'simulation_handler', 'methods': {'POST'}}
"""
import time
with open("example/data.log",mode="a+") as f:
    while 1:
        f.write(str)
        print("append log")
        time.sleep(1)