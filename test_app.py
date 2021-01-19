import pytest

from starlette.testclient import TestClient


@pytest.fixture
def app_client():
    from app import app

    return TestClient(app)


def test_index(app_client: TestClient):
    resp = app_client.get("/")
    assert resp.status_code == 200
    assert "<p>Channels:</p>" in resp.text


def test_add_del_no_id(app_client: TestClient):
    assert app_client.get("/new-channel").status_code == 400
    assert app_client.get("/del-channel").status_code == 400


def test_add_del_valid(app_client: TestClient):
    from app import all_channels

    channel = "test_add_del_valid"

    resp = app_client.get("/new-channel?id=" + channel)
    assert resp.status_code == 200
    assert channel in all_channels

    resp = app_client.get("/del-channel?id=" + channel)
    assert resp.status_code == 200
    assert channel not in all_channels


def test_add_duplicate(app_client: TestClient):
    channel = "test_add_duplicate"

    app_client.get("/new-channel?id=" + channel)
    assert app_client.get("/new-channel?id=" + channel).status_code == 400

    app_client.get("/del-channel?id=" + channel)  # cleanup


def test_del_invalid(app_client: TestClient):
    assert app_client.get("/del-channel?id=test_del_invalid").status_code == 400


def test_push_invalid(app_client: TestClient):
    assert app_client.post("/push/test_push_invalid", {"foo": "bar"}).status_code == 400


def test_adverts(app_client: TestClient):
    channel_one = "test_new_adverts1"
    channel_two = "test_new_adverts2"
    app_client.get("/new-channel?id=" + channel_one)
    with app_client.websocket_connect("/socket") as socket_client:
        # advert of pre-existing
        assert socket_client.receive_json() == {"t": "new", "id": channel_one}

        app_client.get("/new-channel?id=" + channel_two)
        assert socket_client.receive_json() == {"t": "new", "id": channel_two}

        app_client.get("/del-channel?id=" + channel_one)
        assert socket_client.receive_json() == {"t": "del", "id": channel_one}

    app_client.get("/del-channel?id=" + channel_two)  # cleanup


def test_sub_push(app_client: TestClient):
    channel = "test_sub_push"
    app_client.get("/new-channel?id=" + channel)
    with app_client.websocket_connect("/socket") as socket_client:
        app_client.post("/push/" + channel, '"never sent"')

        socket_client.send_text("sub" + channel)
        app_client.post("/push/" + channel, '"is sent"')

        socket_client.receive_json()  # incoming advert
        assert socket_client.receive_json() == {
            "t": "msg",
            "id": channel,
            "msg": "is sent",
        }

    app_client.get("/del-channel?id=" + channel)  # cleanup


def test_resub_push(app_client: TestClient):
    channel = "test_resub_push"
    app_client.get("/new-channel?id=" + channel)
    with app_client.websocket_connect("/socket") as socket_client:
        socket_client.send_text("sub" + channel)

        socket_client.send_text("pop" + channel)
        app_client.post("/push/" + channel, '"never sent"')

        socket_client.send_text("sub" + channel)
        app_client.post("/push/" + channel, '"is sent"')

        assert socket_client.receive_json()["t"] == "new"
        assert socket_client.receive_json() == {
            "t": "msg",
            "id": channel,
            "msg": "is sent",
        }

    app_client.get("/del-channel?id=" + channel)  # cleanup


def test_delete_unsub(app_client: TestClient):
    channel = "test_delete_unsub"
    app_client.get("/new-channel?id=" + channel)
    with app_client.websocket_connect("/socket") as socket_client:
        socket_client.send_text("sub" + channel)
        app_client.post("/push/" + channel, '{"sent": true, "number": 1}')

        app_client.get("/del-channel?id=" + channel)
        app_client.get("/new-channel?id=" + channel)
        app_client.post("/push/" + channel, '{"sent": false, "number": -1}')
        socket_client.send_text("sub" + channel)
        app_client.post("/push/" + channel, '{"sent": true, "number": 2}')

        assert socket_client.receive_json()["t"] == "new"
        assert socket_client.receive_json()["msg"] == {"sent": True, "number": 1}
        assert socket_client.receive_json()["t"] == "del"
        assert socket_client.receive_json()["t"] == "new"
        assert socket_client.receive_json()["msg"] == {"sent": True, "number": 2}

    app_client.get("/del-channel?id=" + channel)  # cleanup


def test_sub_before_create(app_client: TestClient):
    channel = "test_sub_before_create"
    with app_client.websocket_connect("/socket") as socket_client:
        socket_client.send_text("sub" + channel)
        app_client.get("/new-channel?id=" + channel)
        app_client.post("/push/" + channel, "0")
        socket_client.send_text("sub" + channel)
        app_client.post("/push/" + channel, "1")

        assert socket_client.receive_json()["t"] == "new"
        assert socket_client.receive_json()["msg"] == 1

    app_client.get("/del-channel?id=" + channel)  # cleanup


def test_unknown_verb(app_client: TestClient):
    with app_client.websocket_connect("/socket") as socket_client:
        socket_client.send_text("idkhello")
