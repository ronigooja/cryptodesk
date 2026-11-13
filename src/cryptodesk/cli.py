import argparse
import os
from datetime import UTC, datetime, timedelta

from . import check, daily, model, news, profiles, registry, store
from .adapters import binance, cftc, coinmetrics, defillama, deribit, etf, mempool, nyfed, okx, treasury
from .adapters.base import PROXY_ENV, make_get, make_get_text


def make_get_fn():
    return make_get(proxy=os.environ.get(PROXY_ENV) or None)


def make_daily_get_fn():
    return make_get(proxy=os.environ.get(PROXY_ENV) or None, decimal=True)


make_get_text_fn = make_get_text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cryptodesk")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("group", choices=("market", "options", "macro", "onchain", "flows", "news", "daily"))
    backfill = commands.add_parser("backfill")
    backfill.add_argument("--since", type=daily.valid_date, default=daily.START)
    backfill.add_argument("--series", action="append", choices=tuple(daily.SERIES))
    commands.add_parser("check")
    args = parser.parse_args(argv)
    root = store.find_root()
    db = store.Store(root, registry.load(root))
    if args.command == "backfill" or (args.command == "collect" and args.group == "daily"):
        now = datetime.now(UTC)
        series_ids = (args.series or list(daily.SERIES)) if args.command == "backfill" else list(daily.SERIES)
        since = args.since if args.command == "backfill" else now.date() - timedelta(days=5)
        if since >= now.date():
            parser.error("--since must precede today UTC")
        run = daily.DailyStore(root).collect(series_ids, make_daily_get_fn(), make_get_text_fn(), since,
                                             model.iso(now), args.command if args.command == "backfill" else "daily")
        return 1 if run["missing"] == len(series_ids) else 0
    if args.command == "collect":
        started = model.iso(datetime.now(UTC))
        facts = []
        if args.group == "news":
            items, errors, skipped = news.collect(make_get_text_fn(), started)
            run = news.NewsStore(root).apply(items, started, errors, skipped)
            print(f"collect news: facts={run['facts']} changed={run['changed']} "
                  f"unchanged={run['unchanged']} missing={run['missing']}")
            return 0 if items else 1
        if args.group == "macro":
            facts = treasury.collect(make_get_text_fn(), started) + nyfed.collect(make_get_fn(), started)
        elif args.group == "onchain":
            get = make_get_fn()
            facts = defillama.collect(None, get, started)
            for coin in profiles.list_coins(root):
                facts.extend(coinmetrics.collect(coin, get, started))
                facts.extend(mempool.collect(coin, get, started))
        elif args.group == "flows":
            facts = etf.collect(make_get_text_fn(), started)
            get = make_get_fn()
            for coin in profiles.list_coins(root):
                if coin in cftc.MARKETS:
                    facts.extend(cftc.collect(coin, profiles.load(root, coin), get, started))
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
    errors = check.check_all(db, root)
    print(f"check: errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
