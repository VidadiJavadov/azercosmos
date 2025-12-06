from typing import Sequence

from pystac import Item
from pystac.asset import Asset


def resolve_asset(item: Item, candidates: Sequence[str]) -> Asset:
    """
    Return the first Asset from the item whose key is in `candidates`.
    Raises if none are present.
    """
    for name in candidates:
        asset = item.assets.get(name)
        if asset is not None:
            return asset
    raise ValueError(
        f"No asset found for any of {candidates} in item {item.id}. "
        f"Available: {list(item.assets.keys())}"
    )
