import tomllib
from pathlib import Path


def load(root: Path, coin: str) -> dict:
    with (root / "coins" / coin / "profile.toml").open("rb") as fh:
        profile = tomllib.load(fh)
    coin_class = profile.get("class")
    if coin_class not in {"major", "alt"}:
        raise ValueError("profile class must be major or alt")
    if coin_class == "alt":
        raise NotImplementedError("alt is built in phase 4")
    return profile


def list_coins(root: Path) -> list[str]:
    return sorted(p.parent.name for p in (root / "coins").glob("*/profile.toml"))
