import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

from httpx import AsyncClient, Timeout
from pydantic import TypeAdapter
from typing_extensions import AsyncContextManager, AsyncIterator

from cheezen.game import GameState, OngoingGame, OngoingChallenge, GameFinish, GameStart


class LichessAPIEndpoint(str, Enum):
    ACCOUNT = "account"
    ONGOING_GAMES = "account/playing"
    BOT_PLAY_GAME = "bot/game/stream/{game_id}"
    BOT_MAKE_MOVE = "bot/game/{game_id}/move/{move}"
    BOT_SEND_CHAT = "bot/game/{game_id}/chat"
    STREAM_EVENTS = "stream/event"


@dataclass(slots=True)
class LichessClient:
    token: str
    _http_client: AsyncClient = field(default_factory=AsyncClient, init=False)

    def __post_init__(self):
        self._http_client.headers["Authorization"] = "Bearer {}".format(self.token)
        self._http_client.base_url = "https://lichess.org/api/"

    async def send_chat_message(self, game_id: str, text: str):
        await self._http_client.post(LichessAPIEndpoint.BOT_SEND_CHAT.format(game_id=game_id),
                                     data={"text": text, "room": "spectator"})

    async def stream_events(self) -> AsyncIterator[GameState | OngoingChallenge]:
        async with self._http_client.stream(
                "GET", LichessAPIEndpoint.STREAM_EVENTS,
                headers={"Content-Type": "application/x-ndjson"}, timeout=Timeout(5, read=None, write=None, pool=None)
        ) as response:
            async for line in response.aiter_lines():
                if line == "":
                    continue
                event = json.loads(line)
                match event["type"]:
                    case "gameStart":
                        yield GameStart.model_validate(event["game"])
                    case "challenge":
                        yield OngoingChallenge.model_validate(event["challenge"])
                    case "gameFinish":
                        yield GameFinish.model_validate(event["game"])

    async def get_username(self) -> str | None:
        response = await self._http_client.get(LichessAPIEndpoint.ACCOUNT)
        if response.status_code == 200:
            return response.json()["username"]

    async def get_ongoing_games(self):
        response = await self._http_client.get(LichessAPIEndpoint.ONGOING_GAMES)
        response.raise_for_status()
        games = response.json()["nowPlaying"]
        return TypeAdapter(list[GameState]).validate_python(games)

    async def make_move(self, game_id: str, move: str) -> bool:
        response = await self._http_client.post(LichessAPIEndpoint.BOT_MAKE_MOVE.format(game_id=game_id, move=move))
        if response.status_code == 200:
            return True
        return False

    @asynccontextmanager
    async def play_game(self, game_id: str) -> AsyncContextManager[[str], OngoingGame]:
        async with self._http_client.stream(
                "GET", LichessAPIEndpoint.BOT_PLAY_GAME.format(game_id=game_id),
                headers={"Content-Type": "application/x-ndjson"}, timeout=Timeout(5, read=None, write=None, pool=None)
        ) as response:
            response.raise_for_status()
            iterator = response.aiter_lines()
            game = OngoingGame(game_id)
            game.event_handler = asyncio.create_task(game.handle_events(iterator))
            yield game
            game.event_handler.cancel()
            game.event_handler = None
