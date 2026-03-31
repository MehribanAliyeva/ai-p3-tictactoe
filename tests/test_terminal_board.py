import unittest

from gttt.terminal_board import parse_board_rows, render_board


class TerminalBoardTests(unittest.TestCase):
    def test_parse_board_rows(self) -> None:
        text = "---\n-XO\n---\n"
        self.assertEqual(parse_board_rows(text), ["---", "-XO", "---"])

    def test_render_board_with_coords(self) -> None:
        text = "---\n-XO\n---\n"
        rendered = render_board(text, show_coords=True)
        self.assertIn("0 | - - -", rendered)
        self.assertIn("1 | - X O", rendered)

    def test_render_board_without_coords(self) -> None:
        text = "---\n-XO\n---\n"
        rendered = render_board(text, show_coords=False)
        self.assertEqual(rendered.splitlines()[1], "- X O")


if __name__ == "__main__":
    unittest.main()
