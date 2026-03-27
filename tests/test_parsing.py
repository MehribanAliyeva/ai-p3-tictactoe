import unittest

from gttt.parsing import board_map_to_json_dict, parse_board_map, parse_game_details


class ParsingTests(unittest.TestCase):
    def test_parse_game_details_with_nested_json_string(self) -> None:
        payload = {
            "code": "OK",
            "game": '{"gameid":"42","gametype":"TTT","boardsize":"12","target":"6","team1id":"1","team2id":"2","status":"INPROGRESS","moves":"5"}',
        }
        details = parse_game_details(payload)
        self.assertEqual(details.game_id, "42")
        self.assertEqual(details.board_size, 12)
        self.assertEqual(details.target, 6)

    def test_parse_board_map_stringified_json(self) -> None:
        payload = {"code": "OK", "output": '{"1,2":"X","2,2":"O"}'}
        board_map = parse_board_map(payload)
        self.assertEqual(board_map[(2, 1)], "X")
        self.assertEqual(board_map[(2, 2)], "O")

    def test_board_map_roundtrip_uses_server_order(self) -> None:
        board_map = {(2, 1): "X", (2, 2): "O"}
        output = board_map_to_json_dict(board_map)
        self.assertEqual(output["1,2"], "X")
        self.assertEqual(output["2,2"], "O")


if __name__ == "__main__":
    unittest.main()
