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
    parser.add_argument("--no-clear", action="store_true")
    return parser


def _fetch_snapshot(client: APIClient, game_id: str, show_coords: bool) -> tuple[str, str]:
    """Fetch one snapshot and return a display block plus a state signature."""
    details = client.get_game_details(game_id)
    board_text = client.get_board_string(game_id)

    header = "gameId={gid} status={status} moves={moves} turn={turn} winner={winner}".format(
        gid=details.game_id,
        status=details.status,
        moves=details.moves,
        turn=details.turn_team_id or "-",
        winner=details.winner_team_id or "-",
    )
    board_render = render_board(board_text, show_coords=show_coords)
    signature = "|".join(
        [
            str(details.status),
            str(details.moves),
            str(details.turn_team_id),
            str(details.winner_team_id),
            board_text,
        ]
    )
    return f"{header}\n{board_render}", signature


def print_snapshot(client: APIClient, game_id: str, show_coords: bool) -> None:
    """Fetch and print one board snapshot with game metadata."""
    output, _ = _fetch_snapshot(client, game_id, show_coords=show_coords)
    print(output)


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

    previous_signature: str | None = None
    poll_count = 0
    try:
        while True:
            if not args.no_clear:
                # ANSI clear-screen sequence for a live-refresh terminal view.
                print("\033[2J\033[H", end="")
            output, signature = _fetch_snapshot(client, args.game_id, show_coords=not args.no_coords)
            poll_count += 1
            state = "changed" if signature != previous_signature else "no-change"
            previous_signature = signature
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[watch #{poll_count}] {now} state={state}")
            print(output)
            print("\n(Press Ctrl+C to stop watching)")
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
