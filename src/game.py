import math
from typing import List, Optional
import random as rd

from abstract_classes import (
    BaseBoard,
    BaseDice,
    BaseGame,
    BasePlayer,
    BaseProperty,
    StrategyFunc,
)


class Strategies:
    """Definition of different strategies players can use"""

    @staticmethod
    def impulsive(player: "Player", property: "Property") -> bool:
        return True

    @staticmethod
    def demanding(player: "Player", property: "Property") -> bool:
        return property.rent > 50

    @staticmethod
    def cautious(player: "Player", property: "Property") -> bool:
        return player.amount - property.price >= 80

    @staticmethod
    def random(player: "Player", property: "Property") -> bool:
        return rd.choice([True, False])


class Dice(BaseDice):
    def roll(self) -> int:
        return rd.randint(1, 6)


class Player(BasePlayer):
    INITIAL_AMOUNT: int = 300

    def __init__(self, should_buy: StrategyFunc) -> None:
        self._should_buy = should_buy
        self.amount = self.INITIAL_AMOUNT

    def should_buy(self, property: "BaseProperty"):
        return self._should_buy(self, property)


class Property(BaseProperty):
    def __init__(self, price: int):
        self.price = price
        self.rent = int(0.1 * price)
        self.owner = None

    @property
    def is_available(self):
        return self.owner is None


class Board(BaseBoard):
    MIN_PROP_PRICE: int = 100
    MAX_PROP_PRICE: int = 250
    PROP_COUNT: int = 20

    def __init__(self):
        self.properties = [
            Property(rd.randint(self.MIN_PROP_PRICE, self.MAX_PROP_PRICE))
            for _ in range(0, self.PROP_COUNT)
        ]


class Game(BaseGame):
    winner: Optional[BasePlayer] = None
    timeout: bool = False
    MAX_ROUNDS = 1000
    INITIAL_AMOUNT = 300
    PRIZE_ON_ROUND_COMPLETION = 100

    def __init__(self, board, dice, players: List[BasePlayer]) -> None:
        self.board = board
        self.dice = dice
        self.players = players
        self.winner = None

    @property
    def property_count(self):
        return len(self.board.properties)

    def setup(self):
        for p in self.players:
            p.amount = self.INITIAL_AMOUNT
            p.position = 0
        rd.shuffle(self.players)
        self.active_players = self.players
        self.winner = None

    def on_player_bankrupt(self, player: BasePlayer):
        self.active_players.remove(player)
        for prop in self.board.properties:
            if prop.owner == player:
                prop.owner = None

    def on_player_round_completion(self, player: BasePlayer):
        player.amount += self.PRIZE_ON_ROUND_COMPLETION

    def move_player(self, player: BasePlayer, dice_value: int):
        if player.position + dice_value >= self.property_count:
            player.position = (player.position + dice_value) % self.property_count
            for _ in range(
                0, math.floor((player.position + dice_value) / self.property_count) + 1
            ):
                self.on_player_round_completion(player)
        else:
            player.position += dice_value

    def execute_player_turn(self, player: BasePlayer):
        target_property = self.board.properties[player.position]
        if target_property.is_available:
            if player.has_amount_to_buy(target_property) and player.should_buy(
                target_property
            ):
                player.buy(target_property)
        else:
            player.pay_rent(target_property)

    def should_continue(self):
        if len(self.active_players) == 1:
            return False
        if self.round >= self.MAX_ROUNDS:
            self.timeout = True
            return False
        return True

    def finish(self):
        if len(self.active_players) == 1:
            self.winner = self.active_players[0]
        else:
            self.active_players.sort(key=lambda p: p.amount, reverse=True)
            if self.active_players[0].amount == self.active_players[1].amount:
                # in case of two or more tied players...
                tied_players = [
                    p
                    for p in self.active_players
                    if p.amount == self.active_players[0].amount
                ]
                # untie by initial player order
                tied_players.sort(key=lambda p: self.players.index(p))
                self.winner = tied_players[0]
            else:
                self.winner = self.active_players[0]


def run_simulation():
    ITERATIONS_TO_RUN = 300

    board = Board()
    dice = Dice()
    games: List[Game] = []

    for _ in range(0, ITERATIONS_TO_RUN):
        players = [
            Player(Strategies.impulsive),
            Player(Strategies.demanding),
            Player(Strategies.cautious),
            Player(Strategies.random),
        ]
        game = Game(board, dice, players)
        game.play()
        games.append(game)

    # Calculate and display results
    games_finished_by_timeout = len([g for g in games if g.timeout])
    avg_rounds = sum([g.round for g in games]) / len(games)
    print(
        f"{games_finished_by_timeout} games finished by timeout (out of {len(games)})"
    )
    print(f"Average round number: {avg_rounds:.1f}")
    print("Victory rate by player behaviour: ")
    for s in Strategies.__dict__.values():
        if isinstance(s, staticmethod):
            winners = len(
                [g for g in games if g.winner._should_buy.__name__ == str(s.__name__)]
            )
            print(f"{str(s.__name__).title()}: {winners / len(games):.1%}")


if __name__ == "__main__":
    run_simulation()
