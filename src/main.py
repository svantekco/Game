from __future__ import annotations

import argparse
import logging

from .game import Game


def main(argv: list[str] | None = None) -> None:
    """Entry point parsed from command line."""
    parser = argparse.ArgumentParser(description="Run VillageSim")
    parser.add_argument("--seed", type=int, default=None, help="World seed")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--show-fps", action="store_true", help="Display FPS/tick timing"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    game = Game(seed=args.seed)
    game.run(show_fps=args.show_fps)


if __name__ == "__main__":
    main()
