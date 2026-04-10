from enum import Enum, auto


class ModelType(Enum):
    API = auto()
    LOCALE = auto()


class CallType(Enum):
    CARD_GENERATION = auto()
    FILTER_AND_SPLIT = auto()
    CARD_IMPROVEMENT = auto()
