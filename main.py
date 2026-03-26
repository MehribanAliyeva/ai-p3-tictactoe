#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


BASE_URL = "https://www.notexponential.com/aip2pgaming/api/index.php"


class APIError(RuntimeError):
    pass


class CurlApiClient:
    def __init__(self, user_id: str, api_key: str, base_url: str = BASE_URL) -> None:
        self.user_id = str(user_id)
        self.api_key = str(api_key)
        self.base_url = base_url

    def _run_curl(self, method: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cmd = [
            "curl",
            "-sS",
            "-X",
            method.upper(),
        ]

        if method.upper() == "GET":
            url = self.base_url
            if params:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode({k: str(v) for k, v in params.items()})}"
            cmd.append(url)
        else:
            cmd.append(self.base_url)

        cmd.extend(["-H", f"userid: {self.user_id}"])
        cmd.extend(["-H", f"x-api-key: {self.api_key}"])

        payload = data if data is not None else {}
        if method.upper() == "POST":
            for k, v in payload.items():
                cmd.extend(["-d", f"{k}={v}"])

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise APIError(f"curl failed: {proc.stderr.strip() or proc.stdout.strip()}")

        body = proc.stdout.strip()
        if not body:
            raise APIError("Empty response from server")

        # Sometimes mod_security returns HTML.
        if body.startswith("<"):
            raise APIError(body)

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise APIError(f"Non-JSON response: {body}") from exc

        if str(result.get("code", "")).upper() == "FAIL":
            raise APIError(result.get("message", str(result)))

        return result

    def get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_curl("GET", params=params)

    def post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_curl("POST", data=data)

    def create_team(self, name: str) -> Dict[str, Any]:
        return self.post({"type": "team", "name": name})

    def add_member(self, team_id: str, user_id: str) -> Dict[str, Any]:
        return self.post({"type": "member", "teamId": team_id, "userId": user_id})

    def remove_member(self, team_id: str, user_id: str) -> Dict[str, Any]:
        return self.post({"type": "removeMember", "teamId": team_id, "userId": user_id})

    def get_team_members(self, team_id: str) -> Dict[str, Any]:
        return self.get({"type": "team", "teamId": team_id})

    def get_my_teams(self) -> Dict[str, Any]:
        return self.get({"type": "myTeams"})

    def create_game(self, team1: str, team2: str, board_size: int, target: int) -> Dict[str, Any]:
        return self.post(
            {
                "type": "game",
                "teamId1": team1,
                "teamId2": team2,
                "gameType": "TTT",
                "boardSize": board_size,
                "target": target,
            }
        )

    def get_my_games(self, open_only: bool = False) -> Dict[str, Any]:
        return self.get({"type": "myOpenGames" if open_only else "myGames"})

    def get_game_details(self, game_id: str) -> Dict[str, Any]:
        return self.get({"type": "gameDetails", "gameId": game_id})

    def get_board_string(self, game_id: str) -> Dict[str, Any]:
        return self.get({"type": "boardString", "gameId": game_id})

    def get_board_map(self, game_id: str) -> Dict[str, Any]:
        return self.get({"type": "boardMap", "gameId": game_id})

    def get_moves(self, game_id: str, count: int = 10, count_param_name: str = "count") -> Dict[str, Any]:
        return self.get({"type": "moves", "gameId": game_id, count_param_name: count})

    def make_move(self, game_id: str, team_id: str, move: Tuple[int, int]) -> Dict[str, Any]:
        r, c = move
        return self.post({"type": "move", "gameId": game_id, "teamId": team_id, "move": f"{r},{c}"})


@dataclass(frozen=True)
class SearchConfig:
    depth: int = 3
    top_k_moves: int = 12
    neighbor_radius: int = 1


class GeneralizedTTTAgent:
    def __init__(self, board: List[List[str]], target: int, my_symbol: str, opp_symbol: str) -> None:
        self.board = board
        self.n = len(board)
        self.target = target
        self.my_symbol = my_symbol
        self.opp_symbol = opp_symbol

    @staticmethod
    def from_board_string(board_string: str, target: int, my_symbol: str, opp_symbol: str) -> "GeneralizedTTTAgent":
        clean = "".join(ch for ch in board_string if ch in {"X", "O", "-"})
        n_float = math.sqrt(len(clean))
        n = int(n_float)
        if n * n != len(clean):
            raise ValueError(f"Bad board string: {board_string}")
        rows = [list(clean[i * n:(i + 1) * n]) for i in range(n)]
        return GeneralizedTTTAgent(rows, target, my_symbol, opp_symbol)

    def board_to_string(self) -> str:
        return "\n".join(" ".join(row) for row in self.board)

    def empty_cells(self) -> List[Tuple[int, int]]:
        return [(r, c) for r in range(self.n) for c in range(self.n) if self.board[r][c] == "-"]

    def occupied_cells(self) -> List[Tuple[int, int]]:
        return [(r, c) for r in range(self.n) for c in range(self.n) if self.board[r][c] != "-"]

    def is_full(self) -> bool:
        return not self.empty_cells()

    def place(self, move: Tuple[int, int], symbol: str) -> None:
        r, c = move
        self.board[r][c] = symbol

    def unplace(self, move: Tuple[int, int]) -> None:
        r, c = move
        self.board[r][c] = "-"

    def legal_moves(self, radius: int = 1) -> List[Tuple[int, int]]:
        occ = self.occupied_cells()
        if not occ:
            center = self.n // 2
            return [(center, center)] if self.board[center][center] == "-" else self.empty_cells()

        out = set()
        for r, c in occ:
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.n and 0 <= nc < self.n and self.board[nr][nc] == "-":
                        out.add((nr, nc))
        return sorted(out) if out else self.empty_cells()

    def max_consecutive(self, symbol: str) -> int:
        best = 0
        n = self.n

        for r in range(n):
            cur = 0
            for c in range(n):
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)

        for c in range(n):
            cur = 0
            for r in range(n):
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)

        for start_r in range(n):
            r, c, cur = start_r, 0, 0
            while r < n and c < n:
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)
                r += 1
                c += 1
        for start_c in range(1, n):
            r, c, cur = 0, start_c, 0
            while r < n and c < n:
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)
                r += 1
                c += 1

        for start_r in range(n):
            r, c, cur = start_r, n - 1, 0
            while r < n and c >= 0:
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)
                r += 1
                c -= 1
        for start_c in range(n - 1):
            r, c, cur = 0, start_c, 0
            while r < n and c >= 0:
                cur = cur + 1 if self.board[r][c] == symbol else 0
                best = max(best, cur)
                r += 1
                c -= 1

        return best

    def has_winner(self, symbol: str) -> bool:
        return self.max_consecutive(symbol) >= self.target

    def terminal_score(self, depth_left: int) -> Optional[int]:
        if self.has_winner(self.my_symbol):
            return 10_000_000 + depth_left
        if self.has_winner(self.opp_symbol):
            return -10_000_000 - depth_left
        if self.is_full():
            return 0
        return None

    def all_windows(self) -> Iterable[List[str]]:
        t = self.target
        n = self.n

        for r in range(n):
            for c in range(n - t + 1):
                yield [self.board[r][c + k] for k in range(t)]

        for c in range(n):
            for r in range(n - t + 1):
                yield [self.board[r + k][c] for k in range(t)]

        for r in range(n - t + 1):
            for c in range(n - t + 1):
                yield [self.board[r + k][c + k] for k in range(t)]

        for r in range(n - t + 1):
            for c in range(t - 1, n):
                yield [self.board[r + k][c - k] for k in range(t)]

    def evaluate_window(self, window: Sequence[str], symbol: str) -> int:
        other = self.opp_symbol if symbol == self.my_symbol else self.my_symbol
        s = sum(1 for x in window if x == symbol)
        o = sum(1 for x in window if x == other)
        e = sum(1 for x in window if x == "-")

        if s > 0 and o > 0:
            return 0
        if s == self.target:
            return 1_000_000
        if o == self.target:
            return -1_000_000 if symbol == self.my_symbol else 1_000_000
        if o == 0 and s > 0:
            return 10 ** s
        if s == 0 and o > 0:
            return -(10 ** o) if symbol == self.my_symbol else 10 ** o
        return 1 if e == self.target else 0

    def positional_bonus(self, move: Tuple[int, int]) -> int:
        r, c = move
        center = (self.n - 1) / 2.0
        dist = abs(r - center) + abs(c - center)
        return int(20 - 2 * dist)

    def evaluate(self) -> int:
        term = self.terminal_score(0)
        if term is not None:
            return term

        score = 0
        for window in self.all_windows():
            score += self.evaluate_window(window, self.my_symbol)

        score += 500 * self.max_consecutive(self.my_symbol)
        score -= 550 * self.max_consecutive(self.opp_symbol)

        for r in range(self.n):
            for c in range(self.n):
                if self.board[r][c] == self.my_symbol:
                    score += self.positional_bonus((r, c))
                elif self.board[r][c] == self.opp_symbol:
                    score -= self.positional_bonus((r, c))
        return score

    def score_move_ordering(self, move: Tuple[int, int], symbol: str) -> int:
        self.place(move, symbol)
        if self.has_winner(symbol):
            self.unplace(move)
            return 10_000_000
        s = self.evaluate() + self.positional_bonus(move)
        self.unplace(move)
        return s if symbol == self.my_symbol else -s

    def ordered_moves(self, symbol: str, top_k: int, radius: int) -> List[Tuple[int, int]]:
        moves = self.legal_moves(radius)
        scored = [(self.score_move_ordering(m, symbol), m) for m in moves]
        scored.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scored[:top_k]]

    def minimax(self, depth: int, alpha: int, beta: int, maximizing: bool, cfg: SearchConfig) -> Tuple[int, Optional[Tuple[int, int]]]:
        term = self.terminal_score(depth)
        if term is not None:
            return term, None
        if depth == 0:
            return self.evaluate(), None

        if maximizing:
            best_score = -10**18
            best_move = None
            for move in self.ordered_moves(self.my_symbol, cfg.top_k_moves, cfg.neighbor_radius):
                self.place(move, self.my_symbol)
                score, _ = self.minimax(depth - 1, alpha, beta, False, cfg)
                self.unplace(move)
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break
            return best_score, best_move

        best_score = 10**18
        best_move = None
        for move in self.ordered_moves(self.opp_symbol, cfg.top_k_moves, cfg.neighbor_radius):
            self.place(move, self.opp_symbol)
            score, _ = self.minimax(depth - 1, alpha, beta, True, cfg)
            self.unplace(move)
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move

    def choose_move(self, cfg: SearchConfig) -> Tuple[int, int]:
        for move in self.legal_moves(cfg.neighbor_radius):
            self.place(move, self.my_symbol)
            ok = self.has_winner(self.my_symbol)
            self.unplace(move)
            if ok:
                return move

        for move in self.legal_moves(cfg.neighbor_radius):
            self.place(move, self.opp_symbol)
            ok = self.has_winner(self.opp_symbol)
            self.unplace(move)
            if ok:
                return move

        _, move = self.minimax(cfg.depth, -10**18, 10**18, True, cfg)
        if move is None:
            empties = self.empty_cells()
            if not empties:
                raise RuntimeError("No legal moves")
            return empties[0]
        return move


def parse_move_text(move_text: str) -> Tuple[int, int]:
    a, b = move_text.split(",")
    return int(a), int(b)


def extract_any(data: Dict[str, Any], *keys: str) -> Optional[Any]:
    for k in keys:
        if k in data:
            return data[k]
    return None


def normalize_board_string(resp: Dict[str, Any]) -> str:
    for key in ("output", "board", "boardString", "string"):
        val = resp.get(key)
        if isinstance(val, str):
            candidate = "".join(ch for ch in val if ch in {"X", "O", "-"})
            if candidate:
                return candidate
    for val in resp.values():
        if isinstance(val, str):
            candidate = "".join(ch for ch in val if ch in {"X", "O", "-"})
            if candidate:
                return candidate
    raise ValueError(f"Could not parse board string from {resp}")


def guess_target(details: Dict[str, Any], fallback_board_len: int) -> int:
    for key in ("target", "m", "winLength"):
        if details.get(key) is not None:
            return int(details[key])
    return max(3, min(fallback_board_len, fallback_board_len // 2))


def guess_my_symbol(my_team_id: str, details: Dict[str, Any], moves_resp: Optional[Dict[str, Any]], board_string: str) -> Tuple[str, str]:
    moves = moves_resp.get("moves") if isinstance(moves_resp, dict) else None
    if isinstance(moves, list):
        for item in moves:
            if str(item.get("teamId")) == str(my_team_id) and item.get("symbol") in {"X", "O"}:
                s = item["symbol"]
                return s, ("O" if s == "X" else "X")

    team1 = extract_any(details, "teamId1", "team1", "player1")
    team2 = extract_any(details, "teamId2", "team2", "player2")
    if team1 is not None and str(team1) == str(my_team_id):
        return "X", "O"
    if team2 is not None and str(team2) == str(my_team_id):
        return "O", "X"

    x_count = board_string.count("X")
    o_count = board_string.count("O")
    return ("X", "O") if x_count == o_count else ("O", "X")


def auto_choose_and_make_move(client, args):
    details = client.get_game_details(args.game_id)
    board_resp = client.get_board_string(args.game_id)
    board_string = normalize_board_string(board_resp)

    n = int(math.sqrt(len(board_string)))
    target = args.target or guess_target(details, n)

    # Empty board: no need to call moves endpoint
    if board_string.count("X") == 0 and board_string.count("O") == 0:
        moves_resp = {"moves": []}
    else:
        try:
            moves_resp = client.get_moves(
                args.game_id,
                count=max(args.recent_moves_count, 20)
            )
        except Exception:
            moves_resp = {"moves": []}

    my_symbol, opp_symbol = guess_my_symbol(
        args.team_id, details, moves_resp, board_string
    )

    agent = GeneralizedTTTAgent.from_board_string(
        board_string, target, my_symbol, opp_symbol
    )

    cfg = SearchConfig(args.depth, args.top_k_moves, args.neighbor_radius)
    move = agent.choose_move(cfg)

    if args.dry_run:
        return {
            "code": "OK",
            "selectedMove": f"{move[0]},{move[1]}",
            "mySymbol": my_symbol,
            "target": target,
            "board": agent.board_to_string(),
        }

    return client.make_move(args.game_id, args.team_id, move)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generalized Tic Tac Toe CLI using curl subprocess")
    p.add_argument("--user-id", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--base-url", default=BASE_URL)

    sub = p.add_subparsers(dest="command", required=True)

    x = sub.add_parser("create-team")
    x.add_argument("--name", required=True)

    x = sub.add_parser("add-member")
    x.add_argument("--team-id", required=True)
    x.add_argument("--member-user-id", required=True)

    x = sub.add_parser("remove-member")
    x.add_argument("--team-id", required=True)
    x.add_argument("--member-user-id", required=True)

    x = sub.add_parser("team-members")
    x.add_argument("--team-id", required=True)

    sub.add_parser("my-teams")
    x = sub.add_parser("create-game")
    x.add_argument("--team1", required=True)
    x.add_argument("--team2", required=True)
    x.add_argument("--board-size", type=int, required=True)
    x.add_argument("--target", type=int, required=True)

    x = sub.add_parser("my-games")
    x.add_argument("--open-only", action="store_true")

    x = sub.add_parser("game-details")
    x.add_argument("--game-id", required=True)

    x = sub.add_parser("board-string")
    x.add_argument("--game-id", required=True)

    x = sub.add_parser("board-map")
    x.add_argument("--game-id", required=True)

    x = sub.add_parser("moves")
    x.add_argument("--game-id", required=True)
    x.add_argument("--count", type=int, default=10)

    x = sub.add_parser("make-move")
    x.add_argument("--game-id", required=True)
    x.add_argument("--team-id", required=True)
    x.add_argument("--move")
    x.add_argument("--auto", action="store_true")
    x.add_argument("--target", type=int)
    x.add_argument("--depth", type=int, default=3)
    x.add_argument("--top-k-moves", type=int, default=12)
    x.add_argument("--neighbor-radius", type=int, default=1)
    x.add_argument("--recent-moves-count", type=int, default=20)
    x.add_argument("--dry-run", action="store_true")

    return p


def run_command(args: argparse.Namespace) -> Dict[str, Any]:
    client = CurlApiClient(args.user_id, args.api_key, args.base_url)

    if args.command == "create-team":
        return client.create_team(args.name)
    if args.command == "add-member":
        return client.add_member(args.team_id, args.member_user_id)
    if args.command == "remove-member":
        return client.remove_member(args.team_id, args.member_user_id)
    if args.command == "team-members":
        return client.get_team_members(args.team_id)
    if args.command == "my-teams":
        return client.get_my_teams()
    if args.command == "create-game":
        return client.create_game(args.team1, args.team2, args.board_size, args.target)
    if args.command == "my-games":
        return client.get_my_games(args.open_only)
    if args.command == "game-details":
        return client.get_game_details(args.game_id)
    if args.command == "board-string":
        return client.get_board_string(args.game_id)
    if args.command == "board-map":
        return client.get_board_map(args.game_id)
    if args.command == "moves":
        return client.get_moves(args.game_id, args.count)
    if args.command == "make-move":
        if bool(args.move) == bool(args.auto):
            raise ValueError("Use exactly one of --move or --auto")
        if args.move:
            return client.make_move(args.game_id, args.team_id, parse_move_text(args.move))
        return auto_choose_and_make_move(client, args)

    raise ValueError(f"Unknown command: {args.command}")


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_command(args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
