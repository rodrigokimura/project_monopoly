from io import StringIO
import random as rd
from random import Random
import sys
import unittest
from unittest.mock import patch

from game import Board, Dice, Game, Strategies, Player, Property, run_simulation


class TestPlayerBuyBehaviour(unittest.TestCase):
    def setUp(self):
        self.impulsive_player = Player(Strategies.impulsive)
        self.picky_player = Player(Strategies.demanding)
        self.cautious_player = Player(Strategies.cautious)
        self.random_player = Player(Strategies.random)

    def test_impulsive_player(self):
        for i in [0, 100, 200, 1000]:
            self.assertTrue(self.impulsive_player.should_buy(Property(i)))

    def test_picky_player(self):
        self.assertTrue(self.picky_player.should_buy(Property(510)))
        self.assertFalse(self.picky_player.should_buy(Property(500)))
        self.assertFalse(self.picky_player.should_buy(Property(490)))

    def test_cautious_player(self):
        self.assertTrue(self.cautious_player.should_buy(Property(220)))
        self.assertFalse(self.cautious_player.should_buy(Property(221)))

    @patch("game.rd")
    def test_random_player(self, rd: rd):
        # force random to be deterministic
        rd.choice._mock_side_effect = Random(42).choice
        self.assertTrue(self.random_player.should_buy(Property(100)))
        self.assertTrue(self.random_player.should_buy(Property(100)))
        self.assertFalse(self.random_player.should_buy(Property(100)))


class TestPlayerActions(unittest.TestCase):
    def setUp(self):
        self.player = Player(Strategies.impulsive)
        owner = Player(Strategies.impulsive)
        self.property = Property(100)
        self.property.owner = owner

    def test_has_amount_to_buy(self):
        self.player.amount = 100
        self.assertTrue(self.player.has_amount_to_buy(Property(100)))
        self.assertFalse(self.player.has_amount_to_buy(Property(101)))

    def test_buy_should_succeed(self):
        self.player.amount = 100
        property = Property(100)
        self.player.buy(property)
        self.assertEqual(self.player.amount, 0)
        self.assertEqual(property.owner, self.player)

    def test_buy_without_enough_amount_should_fail(self):
        self.player.amount = 99
        property = Property(100)
        with self.assertRaises(ValueError) as context:
            self.player.buy(property)
        self.assertEqual(str(context.exception), "Player does not have enough amount")

    def test_buy_unavailable_property_should_fail(self):
        self.player.amount = 300
        with self.assertRaises(ValueError) as context:
            self.player.buy(self.property)
        self.assertEqual(str(context.exception), "Property is not available")

    def test_pay_rent(self):
        self.player.amount = 100
        self.player.pay_rent(self.property)
        self.assertEqual(self.player.amount, 90)
        self.assertEqual(self.property.owner.amount, 310)


class TestGameRules(unittest.TestCase):
    def setUp(self):
        self.p1 = Player(Strategies.impulsive)
        self.p2 = Player(Strategies.demanding)
        self.p3 = Player(Strategies.cautious)
        self.p4 = Player(Strategies.random)
        self.board = Board()
        self.dice = Dice()

    @patch("game.rd")
    def test_setup_should_randomize_player_order(self, rd):
        # force random to be deterministic
        rd.shuffle._mock_side_effect = Random(42).shuffle
        game = Game(self.board, self.dice, [self.p1, self.p2, self.p3, self.p4])
        game.setup()
        self.assertEqual(game.active_players, [self.p3, self.p2, self.p4, self.p1])
        self.assertEqual(game.players, game.active_players)

    def test_setup_should_reset_position(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        for p in players:
            p.position = 10
        game = Game(self.board, self.dice, players)
        game.setup()
        for p in game.players:
            self.assertEqual(p.position, 0)

    def test_setup_should_set_initial_amount(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        for p in players:
            p.amount = 100
        game = Game(self.board, self.dice, players)
        game.setup()
        for p in game.players:
            self.assertEqual(p.amount, game.INITIAL_AMOUNT)

    def test_on_player_round_completion(self):
        self.p1.amount = 10
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.on_player_round_completion(self.p1)
        self.assertEqual(self.p1.amount, 10 + game.PRIZE_ON_ROUND_COMPLETION)

    def test_move_player_should_set_to_new_position(self):
        self.p1.position = 0
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.move_player(self.p1, 6)
        self.assertEqual(self.p1.position, 6)

    def test_move_player_should_call_on_player_round_completion(self):
        self.p1.position = 19
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        with patch.object(game, "on_player_round_completion") as mock:
            game.move_player(self.p1, 1)
            mock.assert_called_once_with(self.p1)
        self.assertEqual(self.p1.position, 0)

    def test_move_player_should_call_on_player_round_completion_more_than_once(self):
        """This use case will not happen, but it is a good test to ensure different dice ranges"""
        self.p1.position = 9
        players = [self.p1, self.p2, self.p3, self.p4]
        short_board = Board()
        short_board.properties = short_board.properties[:10]
        game = Game(self.board, self.dice, players)
        with patch.object(game, "on_player_round_completion") as mock:
            game.move_player(self.p1, 19)
            mock.assert_called_with(self.p1)
            self.assertEqual(mock.call_count, 2)
        self.assertEqual(self.p1.position, 8)

    def test_execute_player_turn_with_available_property_and_enough_amount_should_use_strategy(
        self,
    ):
        players = [self.p1, self.p2, self.p3, self.p4]
        board = Board()
        board.properties = [Property(100)]
        game = Game(board, self.dice, players)
        game.setup()
        game.move_player(self.p1, 1)
        target_property = board.properties[self.p1.position]
        self.assertTrue(target_property.is_available)
        self.assertTrue(self.p1.has_amount_to_buy(target_property))

        with (
            patch.object(self.p1, "should_buy") as mock_should_buy,
            patch.object(self.p1, "buy") as mock_buy,
        ):
            # will buy when should_buy is True
            mock_should_buy.return_value = True
            game.execute_player_turn(self.p1)
            mock_should_buy.assert_called_once_with(target_property)
            mock_buy.assert_called_once_with(target_property)
        with (
            patch.object(self.p1, "should_buy") as mock_should_buy,
            patch.object(self.p1, "buy") as mock_buy,
        ):
            # will not buy when should_buy is False
            mock_should_buy.return_value = False
            game.execute_player_turn(self.p1)
            mock_should_buy.assert_called_once_with(target_property)
            mock_buy.assert_not_called()

    def test_execute_player_turn_with_available_property_and_not_enough_amount_should_do_nothing(
        self,
    ):
        players = [self.p1, self.p2, self.p3, self.p4]
        board = Board()
        board.properties = [Property(1000)]
        game = Game(board, self.dice, players)
        game.setup()
        game.move_player(self.p1, 1)
        target_property = board.properties[self.p1.position]
        self.assertTrue(target_property.is_available)
        self.assertFalse(self.p1.has_amount_to_buy(target_property))

        with (
            patch.object(self.p1, "should_buy") as mock_should_buy,
            patch.object(self.p1, "buy") as mock_buy,
            patch.object(self.p1, "pay_rent") as mock_pay_rent,
        ):
            game.execute_player_turn(self.p1)
            mock_should_buy.assert_not_called()
            mock_buy.assert_not_called()
            mock_pay_rent.assert_not_called()

    def test_execute_player_turn_with_unavailable_property_should_pay_rent(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        board = Board()
        owned_property = Property(100)
        owned_property.owner = self.p2
        board.properties = [owned_property]
        game = Game(board, self.dice, players)
        game.setup()
        game.move_player(self.p1, 1)
        target_property = board.properties[self.p1.position]
        self.assertFalse(target_property.is_available)

        with (
            patch.object(self.p1, "should_buy") as mock_should_buy,
            patch.object(self.p1, "buy") as mock_buy,
            patch.object(self.p1, "pay_rent") as mock_pay_rent,
        ):
            game.execute_player_turn(self.p1)
            mock_should_buy.assert_not_called()
            mock_buy.assert_not_called()
            mock_pay_rent.assert_called_once_with(target_property)

    def test_on_player_bankrupt_should_remove_and_expropriate_player(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        board = Board()
        owned_property = Property(100)
        owned_property.owner = self.p1
        board.properties = [owned_property]
        game = Game(board, self.dice, players)
        game.setup()
        game.on_player_bankrupt(self.p1)
        self.assertIsNone(owned_property.owner)
        self.assertNotIn(self.p1, game.active_players)

    def test_finish_with_one_active_player_as_winner(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        game.on_player_bankrupt(self.p1)
        game.on_player_bankrupt(self.p2)
        game.on_player_bankrupt(self.p3)
        game.finish()
        self.assertEqual(game.active_players, [self.p4])
        self.assertEqual(game.winner, self.p4)

    def test_finish_with_two_active_players_should_set_winner_by_amount(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        game.on_player_bankrupt(self.p1)
        game.on_player_bankrupt(self.p2)
        self.p3.amount = 100
        self.p4.amount = 1000
        game.finish()
        self.assertIn(self.p3, game.active_players)
        self.assertIn(self.p4, game.active_players)
        self.assertEqual(game.winner, self.p4)

    def test_finish_with_two_tied_players_should_break_tie_by_initial_order(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        initial_order = game.players.copy()
        initial_order.remove(self.p1)
        initial_order.remove(self.p2)
        game.on_player_bankrupt(self.p1)
        self.p2.amount = 10
        game.finish()
        self.assertEqual(game.active_players[0].amount, game.active_players[1].amount)
        self.assertEqual(game.winner, initial_order[0])

    def test_finish_with_three_tied_players_should_also_break_tie_by_initial_order(
        self,
    ):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        initial_order = game.players.copy()
        initial_order.remove(self.p1)
        game.on_player_bankrupt(self.p1)
        game.finish()
        for player in game.active_players:
            self.assertEqual(player.amount, game.active_players[0].amount)
        self.assertEqual(game.winner, initial_order[0])

    def test_should_continue_should_be_true(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        self.assertTrue(game.should_continue())

    def test_should_continue_when_only_one_player_should_be_false(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.active_players = [self.p1]
        self.assertFalse(game.should_continue())

    def test_should_continue_when_round_max_out_should_be_false(self):
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(self.board, self.dice, players)
        game.setup()
        game.round = game.MAX_ROUNDS
        self.assertFalse(game.should_continue())

    @patch("game.rd")
    def test_play_with_fixed_seed_should_succeed(self, rnd):
        rnd.randint._mock_side_effect = Random(42).randint
        rnd.shuffle._mock_side_effect = Random(42).shuffle
        rd.seed(42)
        players = [self.p1, self.p2, self.p3, self.p4]
        game = Game(Board(), Dice(), players)
        game.setup()
        game.play()
        self.assertEqual(game.round, game.MAX_ROUNDS)
        self.assertIs(game.winner, self.p4)


class TestRunSimulation(unittest.TestCase):
    def setUp(self) -> None:
        self.output = StringIO()
        sys.stdout = self.output

    def tearDown(self) -> None:
        sys.stdout = sys.__stdout__

    def test_run_simulation(self):
        rd.seed(42)
        run_simulation()
        printed_text = self.output.getvalue().split("\n")
        self.assertIn("300 games finished by timeout (out of 300)", printed_text)
        self.assertIn("Average round number: 1000.0", printed_text)
        self.assertIn("Impulsive: 23.3%", printed_text)
        self.assertIn("Demanding: 31.7%", printed_text)
        self.assertIn("Cautious: 24.0%", printed_text)
        self.assertIn("Random: 21.0%", printed_text)


if __name__ == "__main__":
    unittest.main()
