from __future__ import annotations

import argparse
import logging

from .multigame import MultiGame


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
    parser.add_argument(
        "--preview", action="store_true", help="Show world preview during startup"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    game = MultiGame(seed=args.seed, preview=args.preview)
    game.run(show_fps=args.show_fps)


if __name__ == "__main__":
    main()
