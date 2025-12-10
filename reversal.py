import click
import backtrader as bt

from data import download


class ReveralStrategy(bt.Strategy):
    def __init__(self):
        self.returns = bt.ind.PercentChange(period=1)
        self.entry_dt = None
        self.barssince = 0

    def notify_order(self, order: bt.Order):
        if order.status == bt.Order.Margin:
            print("Margin")

    def next(self):
        if not self.position.size:
            self.barssince = 0
            if self.returns[0] < -0.01:
                size = self.broker.getvalue() / self.data.close[0]
                self.order_target_size(target=size)
                self.entry_dt = bt.num2date(self.data.datetime[0])
        elif self.position.size > 0:
            self.barssince += 1
            if self.returns[0] > 0.005:
                self.close()
            elif self.barssince >= 5:
                self.close()


@click.command()
@click.option("--symbol", default="ETH/USDT", help="标的标识")
@click.option("--start-date", default="2020-01-01", help="开始时间")
@click.option("--end-date", default="2025-11-30", help="结束时间")
@click.option("--interval", default="1h", help="结束时间")
def main(symbol, start_date, end_date, interval):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcommission(0.001)
    cerebro.addobserver(bt.observers.Value)

    df = download(
        symbol=symbol, start_date=start_date, end_date=end_date, interval=interval
    )
    data = bt.feeds.PandasData(dataname=df)
    data.plotinfo.plot = False
    cerebro.adddata(data)

    cerebro.addstrategy(ReveralStrategy)

    cerebro.run()
    cerebro.plot()


if __name__ == "__main__":
    main()
