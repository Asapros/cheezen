import asyncio
from os import environ

from dotenv import load_dotenv

from cheezen.client import CheezenClient
from cheezen.logger import setup_logger

load_dotenv()


def main():
    setup_logger("logging.yaml")
    token = environ.get("TOKEN")
    engine = environ.get("ENGINE")
    asyncio.run(CheezenClient(token, engine).loop())


if __name__ == "__main__":
    main()
