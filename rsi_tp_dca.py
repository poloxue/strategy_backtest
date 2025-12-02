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
        ("rsi_value", 30),
        ("investment_amount", 100),  # Amount to invest each period
    )

    def __init__(self):
        self.total_invested = 0.0
        self.rsi = bt.indicators.RSI(self.data.close, period=14)  # pyright: ignore
        self.count = 0

    def next(self):
        if self.rsi[0] < self.p.rsi_value and self.count < 20:
            investment_amount = (self.broker.getvalue() - self.total_invested) / (
                20 - self.count
            )
            size = investment_amount / self.data.close[0]
            self.buy(size=size)
            self.total_invested += investment_amount
            self.count += 1

        if self.position.size > 0 and self.count > 0:
            average_price = self.total_invested / self.position.size
            if self.data.close[0] > 1.5 * average_price:
                size = self.position.size / self.count / 3
                self.total_invested *= 1 - size / self.position.size
                self.sell(size=size)
                self.count -= 1


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
@click.option("--rsi-value", default=30.0, help="rsi 阈值)")
def main(symbol, interval, start_date, end_date, plot, rsi_value):
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    cerebro = bt.Cerebro()

    data = download(symbol, interval=interval, start_date=start_date, end_date=end_date)
    data = bt.feeds.PandasData(dataname=data)  # pyright: ignore
    cerebro.adddata(data)

    cerebro.broker.setcash(30000)
    cerebro.broker.setcommission(0.001)

    cerebro.addstrategy(
        DCAStrategy,
        interval=interval,
        rsi_value=rsi_value,
        investment_amount=1000,
    )

    cerebro.addanalyzer(bt.analyzers.timereturn.TimeReturn, _name="timereturn")

    start_value = cerebro.broker.getvalue()
    strat = cerebro.run()
    end_value = cerebro.broker.getvalue()

    print(f"start:{start_value}, end:{end_value}, profit:{end_value - start_value}")

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
