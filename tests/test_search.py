import unittest

from gttt.board import Board
from gttt.models import SearchConfig
from gttt.search import AlphaBetaSearcher


class SearchTests(unittest.TestCase):
    def test_immediate_winning_move_is_selected(self) -> None:
        board = Board.from_board_string("XX-\nOO-\n---")
        searcher = AlphaBetaSearcher(
            board=board,
            target=3,
            my_symbol="X",
            opp_symbol="O",
            search_config=SearchConfig(depth=2, top_k_moves=9, neighbor_radius=2),
        )
        move = searcher.choose_move()
        self.assertEqual((move.x, move.y), (2, 0))

    def test_immediate_block_is_selected(self) -> None:
        board = Board.from_board_string("OO-\nX--\nX--")
        searcher = AlphaBetaSearcher(
            board=board,
            target=3,
            my_symbol="X",
            opp_symbol="O",
            search_config=SearchConfig(depth=2, top_k_moves=9, neighbor_radius=2),
        )
        move = searcher.choose_move()
        self.assertEqual((move.x, move.y), (2, 0))


if __name__ == "__main__":
    unittest.main()
