from dataclasses import dataclass


@dataclass
class OutsideStats:
    """Price history from another site (CamelCamelCamel), so we don't have to wait weeks."""
    normal: float
    lowest: float


@dataclass
class Observation:
    """One price seen today for one item."""
    id: str
    title: str
    store: str
    url: str
    price: float | None
    source: str
    was_price: float | None = None
    outside: OutsideStats | None = None
    image: str | None = None
    interest: str | None = None
    target_price: float | None = None
    error: str | None = None
