import argparse
import os
from datetime import UTC, datetime

from . import check, model, profiles, registry, render, store
from .adapters import binance, deribit, nyfed, okx, treasury
from .adapters.base import PROXY_ENV, make_get, make_get_text


def make_get_fn():
    return make_get(proxy=os.environ.get(PROXY_ENV) or None)


make_get_text_fn = make_get_text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cryptodesk")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("group", choices=("market", "options", "macro"))
    commands.add_parser("render")
    commands.add_parser("check")
    args = parser.parse_args(argv)
    root = store.find_root()
    db = store.Store(root, registry.load(root))
    if args.command == "collect":
        started = model.iso(datetime.now(UTC))
        facts = []
        if args.group == "macro":
            facts = treasury.collect(make_get_text_fn(), started) + nyfed.collect(make_get_fn(), started)
        else:
            get = make_get_fn()
            for coin in profiles.list_coins(root):
                profile = profiles.load(root, coin)
                if args.group == "market":
                    for adapter in (binance.collect, okx.collect, deribit.collect_market):
                        facts.extend(adapter(coin, profile, get, started))
                elif "options" in profile.get("modules", []):
                    facts.extend(deribit.collect_options(coin, profile, get, started))
        run = db.apply(facts, args.group, started)
        print(f"collect {args.group}: facts={run['facts']} changed={run['changed']} "
              f"unchanged={run['unchanged']} missing={run['missing']}")
        return 0 if facts else 1
    if args.command == "render":
        paths = render.render_all(db)
        print(f"render: files={len(paths)}")
        return 0
    errors = check.check_all(db, root)
    print(f"check: errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
