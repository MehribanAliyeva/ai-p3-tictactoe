import unittest

from gttt.coordinates import move_to_server_text, server_pair_to_move, server_text_to_move
from gttt.models import Move


class CoordinateTests(unittest.TestCase):
    def test_server_text_to_move_converts_row_col_to_internal_xy(self) -> None:
        move = server_text_to_move("1,2")
        self.assertEqual(move, Move(x=2, y=1))

    def test_move_to_server_text_converts_internal_xy_to_row_col(self) -> None:
        text = move_to_server_text(Move(x=2, y=1))
        self.assertEqual(text, "1,2")

    def test_server_pair_to_move(self) -> None:
        move = server_pair_to_move(3, 4)
        self.assertEqual(move, Move(x=4, y=3))


if __name__ == "__main__":
    unittest.main()
