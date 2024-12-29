import asyncio
import os.path
import secrets
from asyncio import Future
from dataclasses import dataclass, field

from cheezen.api import LichessClient
from cheezen.game import PieceColor, EventGameState, OngoingGame, GameFinish, GameStart
from cheezen.logger import logger


@dataclass(slots=True)
class CheezenClient(LichessClient):
    executable_path: str
    _game_handlers: dict[str, Future] = field(default_factory=dict, init=False)

    async def run_engine(self, moves: str, black_time: int, white_time: int) -> str | None:
        process = await asyncio.create_subprocess_exec(
            self.executable_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            text=False
        )
        moves_made = len(moves.split(" "))
        if moves == "":
            moves_made = 0
        engine_input = "{} {} {} {}".format(white_time, black_time, moves_made, moves)
        stdout, stderr = await process.communicate(input=engine_input.encode("ascii"))
        if process.returncode != 0:
            logger.error("Engine exited with status code {}, captured stdout: {}"
                         .format(process.returncode, stdout.decode("utf-8").strip()))
            return None

        return stdout.decode("utf-8").strip()

    async def _handle_invalid_move(self, game: OngoingGame):
        key = secrets.token_hex(3)
        logger.error("({}) Invalid move. Waiting for human intervention. Key: {}".format(game.game_id, key))
        await self.send_chat_message(game.game_id, "Engine calculated an invalid move. See the logs for chat key.")
        while True:
            message = (await game.receive_chat()).text

            if not message.startswith(key):
                continue

            move = message.lstrip(key).strip()
            logger.debug("({}) Submitting a human move: {}".format(game.game_id, move))
            success = await self.make_move(game.game_id, move)
            if success:
                break
            key = secrets.token_hex(3)
            logger.error("({}) Invalid human move. New key: {}".format(game.game_id, key))
            await self.send_chat_message(game.game_id, "That's not even a valid move bro. See logs for a new key.")

    async def handle_external_events(self):
        async for event in self.stream_events():
            if isinstance(event, GameFinish):
                logger.info("Stopping handling game: {}. Won? {}".format(event.game_id, event.color == event.winner))
                self._game_handlers.pop(event.game_id).cancel()
            if isinstance(event, GameStart):
                logger.info("Handling game: {}. Playing {}".format(event.game_id, event.color.value))
                self._game_handlers[event.game_id] = asyncio.create_task(self.handle_game(event.game_id, event.color))
                continue

    async def handle_game(self, game_id: str, color: PieceColor):
        async with self.play_game(game_id) as game:
            while True:
                state: EventGameState = await game.receive_state()
                logger.debug("({}) State updated".format(game_id))
                if state.on_turn is not color:
                    logger.debug("({}) Own move. Skipping".format(game_id))
                    continue
                logger.debug("({}) On turn. Running the engine...".format(game_id))
                move = await self.run_engine(state.moves, state.btime, state.wtime)
                logger.debug("({}) Making move: {}".format(game_id, move))
                if move is None or not await self.make_move(game_id, move):
                    await self._handle_invalid_move(game)

    async def setup(self):
        logger.info("Using engine {}".format(self.executable_path))
        if self.executable_path is None or not os.path.isfile(self.executable_path):
            raise RuntimeError("Could not find engine executable. Shutting down")

        username = await self.get_username()
        if username is None:
            raise RuntimeError("Invalid token. Could not log in. Shutting down")
        logger.info("Playing as {}".format(await self.get_username()))

    async def loop(self):
        try:
            await self.setup()
        except RuntimeError as error:
            logger.critical(error)
            return
        try:
            await asyncio.gather(*self._game_handlers.values(), asyncio.create_task(self.handle_external_events()))
        except asyncio.CancelledError:
            logger.critical("Handling cancelled. Shutting down")
