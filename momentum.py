import backtrader as bt
import backtrader.indicators as btind
import yfinance as yf

from data import download
import warnings

warnings.filterwarnings("ignore")


class MomentumStrategy(bt.Strategy):
    def __init__(self):
        self.pchgs = {}
        for data in self.datas:
            self.pchgs[data] = btind.PercentChange(data, period=1)

        self.count = len(self.datas)
        self.cut_pos = int(self.count / 2)

    def notify_order(self, order: bt.Order):
        if order.status == bt.Order.Margin:
            print("Order is Margin")

    def next(self):
        sorted_datas = sorted(
            self.pchgs.keys(),
            key=lambda k: self.pchgs[k][0],
        )

        total_value = self.broker.getvalue()
        target_value = total_value / self.count
        for data in sorted_datas[: self.cut_pos]:
            self.order_target_value(data, -target_value)

        for data in sorted_datas[-self.cut_pos :]:
            self.order_target_value(data, target_value)


if __name__ == "__main__":
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addobserver(bt.observers.Broker)

    cerebro.broker.setcash(1e8)
    cerebro.broker.setcommission(commission=0.0005)
    cerebro.broker.set_slippage_perc(0.0001)

    cerebro.addanalyzer(bt.analyzers.drawdown.DrawDown, _name="drawdown")

    symbols = [
        "BTC/USDT",
        "ETH/USDT",
        "XRP/USDT",
        "BNB/USDT",
        "SOL/USDT",
        "TRX/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "BCH/USDT",
        "LINK/USDT",
    ]
    # symbols = [
    #     "BTC-USD",
    #     "ETH-USD",
    #     "XRP-USD",
    #     "BNB-USD",
    #     "SOL-USD",
    #     # "TRX/USD",
    #     "DOGE-USD",
    #     "ADA-USD",
    #     "BCH-USD",
    #     # "LINK/USDT",
    # ]
    # symbols = ["GOOG", "AAPL", "MSFT", "AMZN", "NVDA", "META"]
    if len(symbols) % 2 != 0:
        raise ValueError(f"标的个数是{len(symbols)}, 无法被2整除")

    for symbol in symbols:
        df = download(
            symbol, start_date="2020-01-01", end_date="2025-11-30", interval="1w"
        )
        # df = yf.download(
        #     symbol,
        #     start="2021-01-01",
        #     end="2025-11-30",
        #     interval="1wk",
        #     multi_level_index=False,
        # )

        data = bt.feeds.PandasData(
            dataname=df,
            name=symbol,
        )
        data.plotinfo.plot = False
        cerebro.adddata(data)

    cerebro.addstrategy(MomentumStrategy)

    print(f"初始持仓价值：{cerebro.broker.getvalue()}")
    strats = cerebro.run()
    print(f"最终持仓价值：{cerebro.broker.getvalue()}")
    max_drawdown = (
        strats[0].analyzers.getbyname("drawdown").get_analysis()["max"]["drawdown"]
    )
    print(f"最大回撤：{max_drawdown}")
    cerebro.plot()
