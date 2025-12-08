import backtrader as bt
import numpy as np
import click
import yfinance as yf

import warnings


warnings.filterwarnings("ignore")


class VolTarget(bt.Strategy):
    params = (
        ("period", 20),
        ("target_vol", 0.15),
        ("annual_factor", 252),
    )

    def __init__(self):
        returns = bt.ind.PercentChange(self.data.close, period=1)
        std_dev = bt.ind.StandardDeviation(returns, period=self.p.period, plot=False)

        self.volatility = std_dev * np.sqrt(self.p.annual_factor)

    def notify_order(self, order: bt.Order):
        if order.status == bt.Order.Margin:
            print("Order is Margin")
        elif order.status == bt.Order.Completed:
            print("Order is Completed")

    def next(self):
        # target_percent = min(self.p.target_vol / self.volatility[0], 1.5)
        # self.order_target_percent(target=target_percent)
        # return
        target_percent = min(self.p.target_vol / self.volatility[0], 1.5)
        print(target_percent)
        target_size = self.broker.getvalue() / self.data.close[0] * target_percent
        self.order_target_size(target=target_size)

    def stop(self):
        print(self.broker.getvalue())


@click.command()
@click.option("--symbol", default="BTC-USD", help="")
def main(symbol):
    cerebro = bt.Cerebro(stdstats=False)

    cerebro.broker.setcash(1e8)
    cerebro.broker.setcommission(
        0.0005,
        commtype=bt.CommInfoBase.COMM_PERC,
        # automargin=True,
        # leverage=2,
    )
    # cerebro.broker.set_coc(True)
    # cerebro.broker.set_slippage_perc(0.0000)

    cerebro.addanalyzer(bt.analyzers.DrawDown)
    df = yf.download(
        symbol,
        start="2015-01-01",
        end="2025-11-30",
        multi_level_index=False,
        auto_adjust=True,
    )
    data = bt.feeds.PandasData(dataname=df, name=symbol)
    data.plotinfo.plot = False
    cerebro.adddata(data)

    cerebro.addobserver(bt.observers.Cash)
    cerebro.addobserver(
        bt.observers.Benchmark, data=data, timeframe=bt.TimeFrame.NoTimeFrame
    )

    cerebro.addstrategy(VolTarget)

    cerebro.run()
    cerebro.plot()

    bt.CommissionInfo
    bt.BackBroker


if __name__ == "__main__":
    main()
