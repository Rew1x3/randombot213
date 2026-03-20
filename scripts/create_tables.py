import asyncio

from database.session import init_db


def main() -> None:
    asyncio.run(init_db())


if __name__ == "__main__":
    main()

