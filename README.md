This is a demo of using the Python [Starlette](https://github.com/encode/starlette)
framework for websockets-based subscription to server events on multiple, dynamically
created and deleted channels.

Run with

```shell
pipenv --python 3.8
pipenv shell
pipenv install
uvicorn starlette_websocket_demo:app
```

# Protocol

This is meant to be server-sent events, which are implemented via the websockets.
However, for convenient usage demonstration, there are some HTTP endpoints for channel
management and sending messages

## Websocket protocol

### Client messages

- `subtest123`: subscribe me to channel `test123`
- `poptest123`: unsubscribe me from channel `test123`

### Server messages

JSON formatted. Message type is stored in field `t`, channel id is in field `id`.

- type `new`: new channel advertisement – means that the given channel was just created
  and can be subscribed to
- type `del`: channel deletion notice – the given channel was deleted, and the client
  automatically unsubscribed
- type `msg`: incoming message – a message was sent to the given channel, the message
  data are stored under the field `msg` (can be structured data)

All channels are automatically unsubscribed upon disconnection (from any side). No
messages are preserved on server, they are just sent to all clients subscribed to the
given channel at the moment the message was received.

## HTTP endpoints

- `GET /new-channel?id={id}` – create a channel with the given ID (will be immediately
  advertised to clients)
- `GET /del-channel?id={id}` – delete the channel with the given ID
- `POST /push/{id}` – send a message to the channel with the given ID, the data
  is `application/json` in the request body
