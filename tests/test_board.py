import unittest

from gttt.board import Board
from gttt.models import Move


class BoardTests(unittest.TestCase):
    def test_parse_board_from_multiline_string(self) -> None:
        board = Board.from_board_string("XX-\n-O-\n---")
        self.assertEqual(board.size, 3)
        self.assertEqual(board.cell(Move(0, 0)), "X")
        self.assertEqual(board.cell(Move(1, 1)), "O")

    def test_candidate_moves_prefers_center_on_empty_board(self) -> None:
        board = Board.from_board_string("---\n---\n---")
        moves = board.candidate_moves(radius=1)
        self.assertEqual(moves, [Move(1, 1)])

    def test_detects_diagonal_winner(self) -> None:
        board = Board.from_board_string("X--\n-X-\n--X")
        self.assertTrue(board.has_winner("X", 3))


if __name__ == "__main__":
    unittest.main()
