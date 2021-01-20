import asyncio
from typing import Dict, Set, Tuple

from starlette.websockets import WebSocket, WebSocketDisconnect

sockets_index: Dict[int, Tuple[WebSocket, Set[str]]] = dict()
all_channels = set()


async def advertise_channel(channel: str, socket: WebSocket, delete: bool = False):
    await socket.send_json({"t": "del" if delete else "new", "id": channel})


async def broadcast_advertise_channel(channel: str, delete: bool = False) -> None:
    await asyncio.gather(
        *[
            advertise_channel(channel, socket, delete)
            for socket, _ in sockets_index.values()
        ]
    )


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
