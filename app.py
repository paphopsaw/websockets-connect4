#!/usr/bin/env python

import asyncio
import websockets
import json
import itertools
from connect4 import PLAYER1, PLAYER2, Connect4
import secrets

JOIN = {}

async def start(websocket):
    game = Connect4()
    connected = {websocket}

    join_key = secrets.token_urlsafe(12)
    JOIN[join_key] = game, connected

    try:
        event = {
            "type": "init",
            "join": join_key,
        }
        await websocket.send(json.dumps(event))

        await play(websocket, game, PLAYER1, connected)

    finally:
        del JOIN[join_key]

async def error(websocket, message):
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(json.dumps(event))

async def join(websocket, join_key):
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    connected.add(websocket)
    try:
        await play(websocket, game, PLAYER2, connected)
    finally:
        connected.remove(websocket)

async def play(websocket, game, player, connected):
    async for message in websocket:
        event = json.loads(message)
        assert event["type"] == "play"
        column = event["column"]

        try:
            row = game.play(player, column)
        except RuntimeError as exc:
            await error(websocket, str(exc))
            continue

        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row
        }
        websockets.broadcast(connected, json.dumps(event))

        if game.winner is not None:
            event = {
                "type": "win",
                "player": game.winner
            }
            websockets.broadcast(connected, json.dumps(event))

async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"

    if "join" in event:
        await join(websocket, event["join"])
    else:
        await start(websocket)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())