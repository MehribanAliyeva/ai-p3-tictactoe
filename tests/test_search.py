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

    def test_iterative_deepening_with_tight_time_budget_returns_legal_move(self) -> None:
        board = Board.from_board_string("-----\n--X--\n--O--\n-----\n-----")
        searcher = AlphaBetaSearcher(
            board=board,
            target=4,
            my_symbol="X",
            opp_symbol="O",
            search_config=SearchConfig(
                depth=6,
                top_k_moves=12,
                neighbor_radius=1,
                max_time_ms=1,
                iterative_deepening=True,
            ),
        )
        move = searcher.choose_move()
        legal = {(m.x, m.y) for m in board.candidate_moves(radius=1)}
        self.assertIn((move.x, move.y), legal)

    def test_transposition_table_is_populated(self) -> None:
        board = Board.from_board_string("-----\n--X--\n--O--\n-----\n-----")
        searcher = AlphaBetaSearcher(
            board=board,
            target=4,
            my_symbol="X",
            opp_symbol="O",
            search_config=SearchConfig(depth=3, top_k_moves=10, neighbor_radius=1),
        )
        _ = searcher.choose_move()
        self.assertGreater(searcher.transposition_size, 0)


if __name__ == "__main__":
    unittest.main()
