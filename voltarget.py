import backtrader as bt
import numpy as np
import click
import yfinance as yf
from analyzers.annualized_volatility import AnnualizedVolatility

import warnings


warnings.filterwarnings("ignore")


class VolTarget(bt.Strategy):
    params = (
        ("period", 20),
        ("target_vol", 0.15),
        ("max_leverage", 1.5),
        ("annual_factor", 252),
    )

    def __init__(self):
        returns = bt.ind.PercentChange(self.data.close, period=1)
        std_dev = bt.ind.StandardDeviation(returns, period=self.p.period, plot=False)

        self.volatility = std_dev * np.sqrt(self.p.annual_factor)

    def notify_order(self, order: bt.Order):
        if order.status == bt.Order.Margin:
            print("Order is Margin")

    def next(self):
        target_percent = min(
            self.p.target_vol / self.volatility[0], self.p.max_leverage
        )
        target_size = self.broker.getvalue() / self.data.close[0] * target_percent
        self.order_target_size(target=target_size)

    def stop(self):
        print("组合价值:", self.broker.getvalue())


@click.command()
@click.option("--symbol", default="SPY", help="")
@click.option("--max-leverage", default=1.5, help="")
@click.option("--target-volatility", default=0.2, help="")
@click.option("--start-date", default="2015-01-01", help="")
@click.option("--end-date", default="2025-11-30", help="")
def main(symbol, max_leverage, target_volatility, start_date, end_date):
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

    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(AnnualizedVolatility, _name="annual_vol")
    df = yf.download(
        symbol,
        start=start_date,
        end=end_date,
        multi_level_index=False,
        auto_adjust=True,
        progress=False,
    )
    data = bt.feeds.PandasData(dataname=df, name=symbol)
    data.plotinfo.plot = False
    cerebro.adddata(data)

    cerebro.addobserver(bt.observers.Cash)
    cerebro.addobserver(
        bt.observers.Benchmark, data=data, timeframe=bt.TimeFrame.NoTimeFrame
    )
    cerebro.addstrategy(
        VolTarget, target_vol=target_volatility, max_leverage=max_leverage
    )

    strats = cerebro.run()

    sharpe_ratio = strats[0].analyzers.getbyname("sharpe").get_analysis()["sharperatio"]
    max_drawdown = (
        strats[0].analyzers.getbyname("drawdown").get_analysis()["max"]["drawdown"]
    )
    annual_volatility = (
        strats[0].analyzers.getbyname("annual_vol").get_analysis()["annual_vol"]
    )
    print("夏普比率:", sharpe_ratio)
    print("最大回撤:", max_drawdown)
    print("年化波动:", annual_volatility)

    cerebro.plot()


if __name__ == "__main__":
    main()
