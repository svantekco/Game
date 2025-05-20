from __future__ import annotations

from .game import Game


def main() -> None:
    game = Game(seed=42)
    game.run()


if __name__ == "__main__":
    main()
