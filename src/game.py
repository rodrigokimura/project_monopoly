import math
from typing import Callable, List, Optional
import random as rd


# Definition of different strategies players can use

StrategyFunc = Callable[["Player", "Property"], bool]


class Strategies:
    @staticmethod
    def impulsive(player: "Player", property: "Property") -> bool:
        return True

    @staticmethod
    def picky(player: "Player", property: "Property") -> bool:
        return property.rent > 50

    @staticmethod
    def cautious(player: "Player", property: "Property") -> bool:
        return player.amount - property.price >= 80

    @staticmethod
    def random(player: "Player", property: "Property") -> bool:
        return rd.choice([True, False])


class Dice:
    def roll(self) -> int:
        return rd.randint(1, 6)


class Player:
    amount: int
    position: int = 0
    INITIAL_AMOUNT: int = 300

    def __init__(self, should_buy: StrategyFunc) -> None:
        self._should_buy = should_buy
        self.amount = self.INITIAL_AMOUNT

    def should_buy(self, property: "Property"):
        return self._should_buy(self, property)

    def has_amount_to_buy(self, property: "Property"):
        return self.amount >= property.price

    def buy(self, property: "Property"):
        if not property.is_available:
            raise ValueError("Property is not available")
        if not self.has_amount_to_buy(property):
            raise ValueError("Player does not have enough amount")
        property.owner = self
        self.amount -= property.price

    def pay_rent(self, property: "Property"):
        property.owner.amount += property.rent
        self.amount -= property.rent

    @property
    def bankrupt(self):
        return self.amount < 0


class Property:
    price: int
    rent: int
    owner: Optional[Player]

    def __init__(self, price: int):
        self.price = price
        self.rent = int(0.1 * price)
        self.owner = None

    @property
    def is_available(self):
        return self.owner is None


class Board:
    MIN_PROP_PRICE: int = 100
    MAX_PROP_PRICE: int = 250
    PROP_COUNT: int = 20

    properties: List[Property]

    def __init__(self):
        self.properties = [
            Property(rd.randint(self.MIN_PROP_PRICE, self.MAX_PROP_PRICE))
            for _ in range(0, self.PROP_COUNT)
        ]


class Game:
    seed: int
    board: Board
    dice: Dice
    players: List[Player]
    active_players: List[Player]
    winner: Optional[Player] = None
    round: int = 0
    timeout: bool = False
    MAX_ROUNDS = 1000
    INITIAL_AMOUNT = 300
    PRIZE_ON_ROUND_COMPLETION = 100

    def __init__(self, board, dice, players: List[Player]) -> None:
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

    def on_player_bankrupt(self, player: Player):
        self.active_players.remove(player)
        for prop in self.board.properties:
            if prop.owner == player:
                prop.owner = None

    def on_player_round_completion(self, player: Player):
        player.amount += self.PRIZE_ON_ROUND_COMPLETION

    def move_player(self, player: Player, dice_value: int):
        if player.position + dice_value >= self.property_count:
            player.position = (player.position + dice_value) % self.property_count
            for _ in range(
                0, math.floor((player.position + dice_value) / self.property_count) + 1
            ):
                self.on_player_round_completion(player)
        else:
            player.position += dice_value

    def execute_player_turn(self, player: Player):
        target_property = self.board.properties[player.position]
        if target_property.is_available:
            if player.has_amount_to_buy(target_property) and player.should_buy(
                target_property
            ):
                player.buy(target_property)
        else:
            player.pay_rent(target_property)

    def should_run(self):
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

    def run(self):
        self.setup()
        while self.should_run():
            for player in self.active_players:
                result = self.dice.roll()
                self.move_player(player, result)
                self.execute_player_turn(player)
                if player.bankrupt:
                    self.on_player_bankrupt(player)
            self.round += 1
        self.finish()


def run_simulation():
    ITERATIONS_TO_RUN = 300

    board = Board()
    dice = Dice()
    games: List[Game] = []

    for _ in range(0, ITERATIONS_TO_RUN):
        players = [
            Player(Strategies.impulsive),
            Player(Strategies.picky),
            Player(Strategies.cautious),
            Player(Strategies.random),
        ]
        game = Game(board, dice, players)
        game.run()
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
