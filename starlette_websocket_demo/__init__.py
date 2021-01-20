import os

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute

from .http import del_channel, index, new_channel, push
from .websockets import socket_endpoint

routes = [
    Route("/", index),
    Route("/push/{channel}", push, methods=["POST"]),
    Route("/new-channel", new_channel),
    Route("/del-channel", del_channel),
    WebSocketRoute("/socket", socket_endpoint),
]

app = Starlette(debug=os.environ.get("DEBUG") == "debug")
