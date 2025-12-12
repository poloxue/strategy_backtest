import os
import click
import ccxt
import pytz
import datetime

import pandas as pd
import numpy as np

from dateutil.parser import parse as datetime_parse
from dateutil.relativedelta import relativedelta

params = {
    "enableRateLimit": True,
    "proxies": {
        "http": os.getenv("http_proxy"),
        "https": os.getenv("http_proxy"),
    },
}

exchanges = {}


def create_exchange(name):
    if name in exchanges:
        return exchanges[name]
    else:
        if not hasattr(ccxt, name):
            raise ValueError(f"Not supported exchange: {name}")
        exchanges[name] = getattr(ccxt, name)(params)
        return exchanges[name]


def symbols(market="swap.linear", quote_ccy="USDT", exchange_name="binance"):
    exchange = create_exchange(exchange_name)
    markets = exchange.load_markets()

    market_type, market_subtype = market.split(".")
    return [
        m["symbol"]
        for m in markets.values()
        if m["active"]
        and m[market_type]
        and m[market_subtype]
        and m["quoteId"] == quote_ccy
    ]


def validate_date_range(start_date, end_date):
    if end_date is None:
        end_date = datetime.datetime.now(pytz.UTC)
    elif isinstance(end_date, str):
        end_date = datetime_parse(end_date)
        end_date = end_date.replace(tzinfo=pytz.UTC)
    else:
        end_date = end_date.replace(tzinfo=pytz.UTC)

    current_date = datetime.datetime.now(pytz.UTC)
    if end_date > current_date:
        end_date = current_date

    if start_date is None:
        start_date = end_date - relativedelta(years=3)
    elif isinstance(start_date, str):
        start_date = datetime_parse(start_date)
        start_date = start_date.replace(tzinfo=pytz.UTC)
    else:
        start_date = start_date.replace(tzinfo=pytz.UTC)

    return start_date, end_date


def download(
    symbol: str, start_date=None, end_date=None, interval="1d", exchange_name="binance"
):
    start_date, end_date = validate_date_range(start_date, end_date)

    exchange = create_exchange(exchange_name)

    max_limit = 100
    since = int(start_date.timestamp() * 1e3)
    end_time = int(end_date.timestamp() * 1e3)

    ohlcvs = []
    while True:
        new_ohlcvs = exchange.fetch_ohlcv(
            symbol=symbol,
            since=since,
            timeframe=interval,
            limit=max_limit,
        )
        new_ohlcvs = [ohlcv for ohlcv in new_ohlcvs if ohlcv[0] <= end_time]
        if len(new_ohlcvs) == 0:
            break
        ohlcvs += new_ohlcvs

        since = ohlcvs[-1][0] + 1000

    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    data = pd.DataFrame(ohlcvs, columns=np.array(columns))
    data.drop_duplicates(inplace=True)
    data["datetime"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
    data.set_index("datetime", inplace=True)
    data.drop(columns=["timestamp"], inplace=True)
    data["symbol"] = symbol

    return data


@click.command()
@click.argument("symbol")
@click.option("--interval", "-i", default="1d", help="时间间隔，默认: 1d")
@click.option("--start", "-s", help="开始时间 YYYY-MM-DD")
@click.option("--end", "-e", help="结束时间 YYYY-MM-DD")
@click.option("--output", "-o", help="输出文件，默认: symbol.csv")
def main(symbol, interval, start, end, output):
    """下载加密货币K线数据到CSV文件"""

    if output is None:
        output = f"{symbol.replace('/', '_')}.csv"

    click.echo(f"下载 {symbol} 数据...")
    click.echo(f"间隔: {interval}")
    click.echo(f"时间范围: {start or '默认'} 到 {end or '默认'}")

    # 下载数据
    data = download(symbol=symbol, start_date=start, end_date=end, interval=interval)

    if data.empty:
        click.echo("错误: 没有获取到数据", err=True)
        return

    # 保存到CSV
    data.to_csv(output)
    click.echo(f"数据已保存到: {output}")
    click.echo(f"共 {len(data)} 条记录")


if __name__ == "__main__":
    main()
