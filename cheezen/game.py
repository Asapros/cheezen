import asyncio
import json
from asyncio import Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PieceColor(str, Enum):
    WHITE = "white"
    BLACK = "black"


class APILoadableModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class GameState(APILoadableModel):
    game_id: str
    color: PieceColor
    fen: str
    has_moved: bool
    is_my_turn: bool
    last_move: str


class EventGameState(APILoadableModel):
    moves: str
    wtime: int
    btime: int
    status: str

    @property
    def on_turn(self) -> PieceColor:
        if self.moves == "":
            return PieceColor.WHITE
        return PieceColor.BLACK if len(self.moves.split(" ")) % 2 else PieceColor.WHITE


class EventGameFull(APILoadableModel):
    initial_fen: str
    created_at: datetime
    state: EventGameState


class EventChatMessage(APILoadableModel):
    text: str


@dataclass(slots=True)
class OngoingGame:
    game_id: str
    event_handler: Future[None] | None = field(default=None, init=False)
    full_game: EventGameFull | None = field(default=None, init=False)
    _state_queue: asyncio.Queue[EventGameState] = field(default_factory=asyncio.Queue, init=False)
    _chat_queue: asyncio.Queue[EventChatMessage] = field(default_factory=asyncio.Queue, init=False)

    async def _handle_event_game_full(self, event: dict):
        self.full_game = EventGameFull.model_validate(event)
        await self._state_queue.put(self.full_game.state)

    async def _handle_event_game_state(self, event: dict):
        model = EventGameState.model_validate(event)
        self.full_game.state = model
        await self._state_queue.put(model)

    async def _handle_event_chat_message(self, event: dict):
        model = EventChatMessage.model_validate(event)
        await self._chat_queue.put(model)

    async def receive_chat(self) -> EventChatMessage:
        return await self._chat_queue.get()

    async def receive_state(self) -> EventGameState:
        state_fetching = asyncio.create_task(self._state_queue.get())
        if self.event_handler is None:
            raise RuntimeError("Game is not listening for events")

        await asyncio.wait([self.event_handler, state_fetching], return_when="FIRST_COMPLETED")
        if self.event_handler.done():
            raise self.event_handler.exception()
        return await state_fetching

    async def handle_events(self, iterator: AsyncIterator[str]):
        async for line in iterator:
            if line == "":
                continue
            event = json.loads(line)
            match event["type"]:
                case "gameFull":
                    await self._handle_event_game_full(event)
                case "gameState":
                    await self._handle_event_game_state(event)
                case "chatLine":
                    await self._handle_event_chat_message(event)


class Challenger(APILoadableModel):
    id: str
    name: str


class OngoingChallenge(APILoadableModel):
    id: str
    challenger: Challenger


class GameStatus(APILoadableModel):
    name: str


class GameFinish(GameState):
    status: GameStatus
    winner: PieceColor | None = None


class GameStart(GameState):
    pass
