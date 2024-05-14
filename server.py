#  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#  ┃ ██████ ██████ ██████       █      █      █      █      █ █▄  ▀███ █       ┃
#  ┃ ▄▄▄▄▄█ █▄▄▄▄▄ ▄▄▄▄▄█  ▀▀▀▀▀█▀▀▀▀▀ █ ▀▀▀▀▀█ ████████▌▐███ ███▄  ▀█ █ ▀▀▀▀▀ ┃
#  ┃ █▀▀▀▀▀ █▀▀▀▀▀ █▀██▀▀ ▄▄▄▄▄ █ ▄▄▄▄▄█ ▄▄▄▄▄█ ████████▌▐███ █████▄   █ ▄▄▄▄▄ ┃
#  ┃ █      ██████ █  ▀█▄       █ ██████      █      ███▌▐███ ███████▄ █       ┃
#  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
#  ┃ Copyright (c) 2017, the Perspective Authors.                              ┃
#  ┃ ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌ ┃
#  ┃ This file is part of the Perspective library, distributed under the terms ┃
#  ┃ of the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). ┃
#  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

import os
import os.path
import logging
import string
import tornado.websocket
import tornado.web
import tornado.ioloop
import threading
import concurrent.futures
import json
import random

from perspective import Table, PerspectiveManager, PerspectiveTornadoHandler


def perspective_thread(manager, table):
    psp_loop = tornado.ioloop.IOLoop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        manager.set_loop_callback(psp_loop.run_in_executor, executor)
        psp_loop.start()


class RPCWebSocket(tornado.websocket.WebSocketHandler):
    """Take a message from teh client, open a file, host the Table under a
    random session name, and return to the UI."""

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop("manager")
        super(RPCWebSocket, self).__init__(*args, **kwargs)

    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        """When a file is requested, read it from disk and load it into a 
        `perspective.Table` under a random name, then return the name to the
        client so that Perspective may open the `Table` virtually via the
        `open_table()` method."""
        path = json.loads(message).get("filepath")
        self.name = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )

        with open(path, "rb") as f:
            self.table = Table(f.read())
            self.manager.host_table(self.name, self.table)

        self.write_message(json.dumps({"table_name": self.name}))

    def on_close(self):
        tornado.ioloop.IOLoop.current().add_timeout(1, lambda: self.table.delete())
        print("WebSocket closed, table deleted")


def make_app():
    manager = PerspectiveManager()
    thread = threading.Thread(target=perspective_thread, args=(manager,))
    thread.daemon = True
    thread.start()

    return tornado.web.Application(
        [
            # RPC protocol on a dedicated WebSocket (which makes it easy to
            # tie the lifetime of the `Table` to the lifetime of the
            # `Websocket`).
            (
                r"/rpc_websocket",
                RPCWebSocket,
                {
                    "manager": manager,
                },
            ),

            # Perspective client get their own websocket
            (
                r"/perspective_websocket",
                PerspectiveTornadoHandler,
                {"manager": manager, "check_origin": True},
            ),
            (
                r"/(.*)",
                tornado.web.StaticFileHandler,
                {"path": "./", "default_filename": "index.html"},
            ),
        ]
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(8080)
    logging.critical("Listening on http://localhost:8080")
    loop = tornado.ioloop.IOLoop.current()
    loop.start()
