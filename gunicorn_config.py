import multiprocessing

bind = "127.0.0.1:8800"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
timeout = 60
keepalive = 2
