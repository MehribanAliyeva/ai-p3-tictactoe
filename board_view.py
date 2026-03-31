#!/usr/bin/env python3
"""Terminal board viewer script.

Author: Kamal Ahmadov
"""

from __future__ import annotations

import argparse
import time

from gttt.api_client import APIClient
from gttt.config import resolve_credentials
from gttt.terminal_board import render_board


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for board snapshots and live watch mode."""
    parser = argparse.ArgumentParser(description="Terminal board viewer for GTTT games")
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--user-id")
    parser.add_argument("--api-key")
    parser.add_argument("--base-url")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--no-coords", action="store_true")
    return parser


def print_snapshot(client: APIClient, game_id: str, show_coords: bool) -> None:
    """Fetch and print one board snapshot with game metadata."""
    details = client.get_game_details(game_id)
    board_text = client.get_board_string(game_id)

    print(
        "gameId={gid} status={status} moves={moves} turn={turn} winner={winner}".format(
            gid=details.game_id,
            status=details.status,
            moves=details.moves,
            turn=details.turn_team_id or "-",
            winner=details.winner_team_id or "-",
        )
    )
    print(render_board(board_text, show_coords=show_coords))


def main() -> int:
    """Run board viewer script."""
    args = build_parser().parse_args()

    creds = resolve_credentials(
        user_id=args.user_id,
        api_key=args.api_key,
        base_url=args.base_url,
        env_file=args.env_file,
    )
    client = APIClient(creds)

    if not args.watch:
        print_snapshot(client, args.game_id, show_coords=not args.no_coords)
        return 0

    try:
        while True:
            # ANSI clear-screen sequence for a live-refresh terminal view.
            print("\033[2J\033[H", end="")
            print_snapshot(client, args.game_id, show_coords=not args.no_coords)
            print("\n(Press Ctrl+C to stop watching)")
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
