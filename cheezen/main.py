import asyncio
from os import environ

from dotenv import load_dotenv

from cheezen.client import CheezenClient
from cheezen.logger import setup_logger

load_dotenv()


def main():
    token = environ.get("TOKEN")
    engine = environ.get("ENGINE")
    log_level = environ.get("LOGLEVEL")
    setup_logger("logging.yaml", log_level)
    asyncio.run(CheezenClient(token, engine).loop())


if __name__ == "__main__":
    main()
