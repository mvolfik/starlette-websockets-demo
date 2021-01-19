import asyncio
from typing import Dict, Set, Tuple

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

sockets_index: Dict[int, Tuple[WebSocket, Set[str]]] = dict()
all_channels = set()


def index(_: Request) -> Response:
    return FileResponse("index.html")


async def push(request: Request) -> Response:
    channel = request.path_params["channel"]
    if channel not in all_channels:
        return PlainTextResponse("Channel doesn't exist", status_code=400)
    data = await request.json()
    await asyncio.gather(
        *[
            socket.send_json({"t": "msg", "id": channel, "msg": data})
            for socket, subscriptions in sockets_index.values()
            if channel in subscriptions
        ]
    )
    return PlainTextResponse("Done")


async def advertise_channel(channel: str, socket: WebSocket, delete: bool = False):
    await socket.send_json({"t": "del" if delete else "new", "id": channel})


async def broadcast_advertise_channel(channel: str, delete: bool = False) -> None:
    await asyncio.gather(
        *[
            advertise_channel(channel, socket, delete)
            for socket, _ in sockets_index.values()
        ]
    )


async def new_channel(request: Request):
    channel = request.query_params.get("id")
    if channel is None or channel in all_channels:
        return PlainTextResponse(
            "Missing or invalid channel identifier", status_code=400
        )
    all_channels.add(channel)
    await broadcast_advertise_channel(channel, False)
    return PlainTextResponse("Done")


async def del_channel(request):
    channel = request.query_params.get("id")
    if channel is None or channel not in all_channels:
        return PlainTextResponse(
            "Missing or invalid channel identifier", status_code=400
        )
    all_channels.discard(channel)
    await broadcast_advertise_channel(channel, True)
    for _, subscriptions in sockets_index.values():
        subscriptions.discard(channel)
    return PlainTextResponse("Done")


async def socket_endpoint(socket):
    await socket.accept()
    sock_id = id(socket)
    subscriptions = set()
    sockets_index[sock_id] = (socket, subscriptions)
    await asyncio.gather(
        *[advertise_channel(channel, socket, False) for channel in all_channels]
    )

    while True:
        try:
            msg = await socket.receive_text()
        except WebSocketDisconnect:
            del sockets_index[sock_id]
            break

        verb = msg[:3]
        if verb == "sub":
            channel = msg[3:]
            if channel in all_channels:
                subscriptions.add(channel)
        elif verb == "pop":
            subscriptions.discard(msg[3:])


routes = [
    Route("/", index),
    Route("/push/{channel}", push, methods=["POST"]),
    Route("/new-channel", new_channel),
    Route("/del-channel", del_channel),
    WebSocketRoute("/socket", socket_endpoint),
]

app = Starlette(debug=True, routes=routes)
