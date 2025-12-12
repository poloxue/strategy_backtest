import click
import pandas as pd
import backtrader as bt


from data import download


class RenkoStrategy(bt.Strategy):
    params = (("break_count", 3),)

    def __init__(self):
        self.atr = bt.ind.ATR(self.data, period=14)
        self.previous_close = None
        self.brick_count = 0

        self.stop_order = None

    def next(self):
        if self.previous_close is None:
            self.previous_close = self.data.close[0]
            return

        change = self.data.close[0] - self.previous_close
        if change > self.atr[0]:
            brick_count = change // self.atr[0]
            if self.brick_count < 0:
                self.brick_count = brick_count
            else:
                self.brick_count += brick_count

            self.previous_close = self.data.close[0]
        elif change < -self.atr[0]:
            brick_count = change // self.atr[0]
            if self.brick_count > 0:
                self.brick_count = brick_count
            else:
                self.brick_count += brick_count
            self.previous_close = self.data.close[0]

        if self.brick_count >= self.p.break_count:
            if self.stop_order:
                self.cancel(self.stop_order)
            if self.position.size < 0:
                self.close()
            if self.position.size <= 0:
                target_size = self.broker.getvalue() / self.data.close[0] * 0.99
                self.order_target_size(target=target_size)
                self.stop_order = self.buy(
                    size=target_size,
                    exectype=bt.Order.Stop,
                    price=self.data.close[0] - 2 * self.atr[0],
                )

        elif self.brick_count <= -self.p.break_count:
            if self.stop_order:
                self.cancel(self.stop_order)
            if self.position.size > 0:
                self.close()
            if self.position.size >= 0:
                target_size = self.broker.getvalue() / self.data.close[0] * 0.99
                self.order_target_size(target=target_size)
                self.stop_order = self.buy(
                    size=target_size,
                    exectype=bt.Order.Stop,
                    price=self.data.close[0] + 2 * self.atr[0],
                )


@click.command()
@click.option("--symbol", default="BTC/USDT")
@click.option("--datafile")
@click.option("--interval", default="1h")
@click.option("--start-date", default="2020-01-01")
@click.option("--end-date", default="2025-11-30")
@click.option("--break-count", default=3)
def main(symbol, datafile, interval, start_date, end_date, break_count):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(1e8)
    cerebro.broker.setcommission(0.0005)

    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.BuySell)

    if datafile:
        df = pd.read_csv(datafile, parse_dates=["datetime"], index_col=[0])
    else:
        df = download(
            symbol, start_date=start_date, end_date=end_date, interval=interval
        )

    data = bt.feeds.PandasData(dataname=df)
    data.plotinfo.plot = False
    cerebro.adddata(data)

    cerebro.addstrategy(RenkoStrategy, break_count=break_count)
    cerebro.run()

    cerebro.plot(style="candlestick")


if __name__ == "__main__":
    main()
