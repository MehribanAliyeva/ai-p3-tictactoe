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

    def test_ordered_moves_preserves_double_threat_blocks_beyond_top_k(self) -> None:
        board = Board.from_board_string(
            "-------\n"
            "-------\n"
            "-------\n"
            "-XXXX--\n"
            "-------\n"
            "-------\n"
            "-------"
        )
        searcher = AlphaBetaSearcher(
            board=board,
            target=5,
            my_symbol="O",
            opp_symbol="X",
            search_config=SearchConfig(depth=2, top_k_moves=1, neighbor_radius=1),
        )
        ordered = searcher._ordered_moves("O")
        coords = {(move.x, move.y) for move in ordered}
        self.assertIn((0, 3), coords)
        self.assertIn((5, 3), coords)

    def test_ordered_moves_prioritizes_forcing_double_threat_creation(self) -> None:
        board = Board.from_board_string(
            "-------\n"
            "-------\n"
            "-------\n"
            "--OO-O-\n"
            "-------\n"
            "-------\n"
            "-------"
        )
        searcher = AlphaBetaSearcher(
            board=board,
            target=5,
            my_symbol="O",
            opp_symbol="X",
            search_config=SearchConfig(depth=1, top_k_moves=8, neighbor_radius=1),
        )
        ordered = searcher._ordered_moves("O")
        self.assertEqual((ordered[0].x, ordered[0].y), (4, 3))

    def test_choose_move_prefers_safe_double_threat(self) -> None:
        board = Board.from_board_string(
            "-------\n"
            "-------\n"
            "-------\n"
            "--OO-O-\n"
            "-------\n"
            "-------\n"
            "-------"
        )
        searcher = AlphaBetaSearcher(
            board=board,
            target=5,
            my_symbol="O",
            opp_symbol="X",
            search_config=SearchConfig(depth=2, top_k_moves=10, neighbor_radius=1),
        )
        move = searcher.choose_move()
        self.assertEqual((move.x, move.y), (4, 3))


if __name__ == "__main__":
    unittest.main()
