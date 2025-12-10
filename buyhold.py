import backtrader as bt

from data import download


class BuyHoldStrategy(bt.Strategy):
    def __init__(self):
        pass

    def notify_order(self, order: bt.Order):
        if order.status == bt.Order.Margin:
            print("Margin")

    def next(self):
        if not self.position.size:
            target_size = self.broker.getvalue() / self.data.close[0]
            self.order_target_size(target=target_size)


def main():
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(1e8)
    cerebro.broker.setcommission(0.001, leverage=2.0)

    df = download(
        symbol="BTC/USDT", start_date="2020-01-01", end_date="2025-11-30", interval="1d"
    )
    data = bt.feeds.PandasData(dataname=df)
    data.plotinfo.plot = False
    cerebro.adddata(data)

    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(
        bt.observers.Benchmark, data=data, timeframe=bt.TimeFrame.NoTimeFrame
    )

    cerebro.addstrategy(BuyHoldStrategy)

    cerebro.run()
    cerebro.plot()


if __name__ == "__main__":
    main()
