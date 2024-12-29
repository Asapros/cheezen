cheezen
=======

A simple tool for running a [lichess](https://lichess.org/) bot.

The functionality is limited and the package is unlikely to be further maintained, because the project has been made specifically to host a local chess engine jam. For more capable lichess bot tool see e.g. the official [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot).

Usage
-----
Install the project with python *poetry* tool. Set `TOKEN` and `ENGINE` environment variables to lichess bot token and engine executable path respectively. You can also use a `.env` file to store configuration. Use `poetry run start` to start the bot.
Logging configuration is stored in `logging.yaml`. You can also use the `LOGLEVEL` environment variable to ignore some logs.

Interface
---------
On each turn, the bot will run the engine executable and write one line to its stdin. The line consists of values separated by a single space character:
1. White time left on clock
2. Black time left on clock
3. Number of moves made so far
4. All the moves in order, separated by spaces, in [UCI format](https://en.wikipedia.org/wiki/Universal_Chess_Interface)

The engine should return any valid move it the current position and write it to stdout (also in the UCI format), terminated with an endline character.

### Engine mistakes
1. When the engine returns a non-zero exit code, stderr content will be available in logs and no stdout will be read.
2. When the move is invalid or not provided at all, the bot will show a log message with a key. The key should be sent in the game's chat by a spectating player along with a correct move: `<key> <move, UCI format>`. The bot will then override the engine's mistake with user input.
