import pandas as pd
import datetime
import matplotlib.pyplot as plt

import click
import backtrader as bt

from data import download

import warnings

warnings.filterwarnings("ignore")


def strategy_title(interval):
    if interval == "1w":
        return "每周"
    elif interval == "1d":
        return "每日"
    elif interval == "4h":
        return "每四时"
    elif interval == "1h":
        return "每小时"


class DCAStrategy(bt.Strategy):
    params = (
        ("interval", "1d"),
        ("investment_amount", 100),  # Amount to invest each period
    )

    def __init__(self):
        self.total_invested = 0.0
        self.bbands = bt.indicators.BollingerBands(
            self.data.close,  # pyright: ignore
            period=20,
            devfactor=2,
        )
        self.botband = self.bbands.bot

        self.count = 0

    def next(self):
        if self.data.close[0] < self.botband[0]:
            size = self.p.investment_amount / self.data.close[0]
            self.buy(size=size)
            self.total_invested += self.p.investment_amount
            self.count += 1

    def stop(self):
        title = strategy_title(self.p.interval)
        if self.position.size:
            average_price = self.total_invested / self.position.size
        else:
            average_price = 0

        print(f"{title} | {average_price:.2f} | {self.count}")


@click.command()
@click.option("--symbol", default="BTC/USDT", help="交易对符号")
@click.option(
    "--interval",
    default="1d",
    type=click.Choice(["1h", "4h", "1d", "1w"]),
    help="投资间隔",
)
@click.option("--start-date", default="2020-01-01", help="开始日期 (YYYY-MM-DD格式)")
@click.option("--end-date", default="2024-12-31", help="结束日期 (YYYY-MM-DD格式)")
@click.option("--plot", is_flag=True, help="是否绘图)")
def main(symbol, interval, start_date, end_date, plot):
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    cerebro = bt.Cerebro()

    data = download(symbol, interval=interval, start_date=start_date, end_date=end_date)
    data = bt.feeds.PandasData(dataname=data)  # pyright: ignore
    cerebro.adddata(data)

    cerebro.broker.setcash(1e8)
    cerebro.broker.setcommission(0.001)

    cerebro.addstrategy(
        DCAStrategy,
        interval=interval,
        investment_amount=1000,
    )

    cerebro.addanalyzer(bt.analyzers.timereturn.TimeReturn, _name="timereturn")
    strat = cerebro.run()

    if not plot:
        return
    returns = strat[0].analyzers.getbyname("timereturn").get_analysis()
    returns_series = pd.Series(returns)
    net_value = (1 + returns_series).cumprod()
    ax = net_value.plot(title="Returns", figsize=(12, 5))

    end_value = net_value.iloc[-1]
    end_index = net_value.index[-1]

    ax.text(
        end_index,
        end_value,
        f"End: {end_value:.2f}",
        ha="right",
        va="top",
        bbox=dict(facecolor="white", alpha=0.8),
    )

    plt.show()


if __name__ == "__main__":
    main()
