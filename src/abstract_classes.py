from abc import ABC, abstractmethod
from typing import Callable, List, Optional


class BaseDice(ABC):
    @abstractmethod
    def roll(self) -> int:
        ...


class BasePlayer(ABC):
    amount: int
    position: int

    @abstractmethod
    def should_buy(self, property: "BaseProperty") -> bool:
        ...

    def has_amount_to_buy(self, property: "BaseProperty"):
        return self.amount >= property.price

    def buy(self, property: "BaseProperty"):
        if not property.is_available:
            raise ValueError("Property is not available")
        if not self.has_amount_to_buy(property):
            raise ValueError("Player does not have enough amount")
        property.owner = self
        self.amount -= property.price

    def pay_rent(self, property: "BaseProperty"):
        property.owner.amount += property.rent
        self.amount -= property.rent

    @property
    def bankrupt(self):
        return self.amount < 0


class BaseProperty(ABC):
    price: int
    rent: int
    owner: Optional[BasePlayer]

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


StrategyFunc = Callable[[BasePlayer, BaseProperty], bool]


class BaseBoard(ABC):
    properties: List[BaseProperty]


class BaseGame(ABC):
    board: BaseBoard
    dice: BaseDice
    active_players: List[BasePlayer]
    round: int = 0

    @abstractmethod
    def setup():
        ...

    @abstractmethod
    def should_continue(self) -> bool:
        ...

    @abstractmethod
    def move_player(self, player: BasePlayer):
        ...

    @abstractmethod
    def execute_player_turn(self):
        ...

    @abstractmethod
    def on_player_bankrupt(self):
        ...

    @abstractmethod
    def finish(self):
        ...

    def play(self):
        self.setup()
        while self.should_continue():
            for player in self.active_players:
                result = self.dice.roll()
                self.move_player(player, result)
                self.execute_player_turn(player)
                if player.bankrupt:
                    self.on_player_bankrupt(player)
            self.round += 1
        self.finish()
