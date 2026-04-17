import unittest

from gttt.agent import choose_auto_move, infer_symbols
from gttt.board import Board
from gttt.models import GameDetails, SearchConfig


class _FakeClient:
    def __init__(self, details: GameDetails, board_text: str, moves_payload: dict[str, object]) -> None:
        self._details = details
        self._board_text = board_text
        self._moves_payload = moves_payload

    def get_game_details(self, game_id: str) -> GameDetails:
        return self._details

    def get_board_string(self, game_id: str) -> str:
        return self._board_text

    def get_moves_raw(self, game_id: str, count: int = 20) -> dict[str, object]:
        return self._moves_payload


class AgentTests(unittest.TestCase):
    def test_infer_symbols_uses_status_turn_for_opening_symbol(self) -> None:
        board = Board.from_board_string("---\n---\n---")
        details = GameDetails(
            game_id="1",
            game_type="TTT",
            board_size=3,
            target=3,
            team1_id="1487",
            team1_name="A",
            team2_id="1480",
            team2_name="B",
            status="O",
            moves=0,
            turn_team_id="1487",
            winner_team_id=None,
            seconds_per_move=600,
        )
        my_symbol, opp_symbol = infer_symbols("1487", details, None, board)
        self.assertEqual((my_symbol, opp_symbol), ("O", "X"))

    def test_infer_symbols_prefers_moves_payload_over_team_order(self) -> None:
        board = Board.from_board_string("---\n---\n---")
        details = GameDetails(
            game_id="2",
            game_type="TTT",
            board_size=3,
            target=3,
            team1_id="1487",
            team1_name="A",
            team2_id="1480",
            team2_name="B",
            status="INPROGRESS",
            moves=1,
            turn_team_id="1480",
            winner_team_id=None,
            seconds_per_move=600,
        )
        payload = {
            "moves": [
                {"teamId": "1487", "symbol": "O", "move": "1,1"},
            ]
        }
        my_symbol, opp_symbol = infer_symbols("1487", details, payload, board)
        self.assertEqual((my_symbol, opp_symbol), ("O", "X"))

    def test_choose_auto_move_uses_status_symbol_when_board_is_empty(self) -> None:
        details = GameDetails(
            game_id="3",
            game_type="TTT",
            board_size=5,
            target=4,
            team1_id="1487",
            team1_name="A",
            team2_id="1480",
            team2_name="B",
            status="O",
            moves=0,
            turn_team_id="1487",
            winner_team_id=None,
            seconds_per_move=600,
        )
        board_text = ("-----\n" * 5).strip()
        client = _FakeClient(details=details, board_text=board_text, moves_payload={"moves": []})

        decision, _board, _details = choose_auto_move(
            client=client,
            game_id="3",
            team_id="1487",
            search_config=SearchConfig(depth=1, top_k_moves=8, neighbor_radius=1),
            verify_turn=True,
        )
        self.assertEqual(decision.my_symbol, "O")


if __name__ == "__main__":
    unittest.main()
