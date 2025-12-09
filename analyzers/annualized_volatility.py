# -*- coding: utf-8 -*-
import math
import numpy as np

from backtrader import Analyzer, TimeFrame
from backtrader.analyzers import TimeReturn
from backtrader.mathsupport import standarddev
from backtrader.utils.py3 import itervalues


class AnnualizedVolatility(Analyzer):
    """
    基于 TimeReturn 的年化波动率分析器（参考 SharpeRatio 的实现方式）

    Params:
      - timeframe (default TimeFrame.Days)
      - compression (default 1)
      - factor (default None) : 手动指定周期->年化因子
      - use_log (default False) : 是否将每周期收益转换为对数收益 ln(1+r)
      - stddev_sample (default False) : 是否使用样本标准差（Bessel 修正）
      - fund (default None) : 同 TimeReturn 的 fund 参数
    """

    params = (
        ("timeframe", TimeFrame.Days),
        ("compression", 1),
        ("factor", None),
        ("use_log", False),
        ("stddev_sample", False),
        ("fund", None),
    )

    RATEFACTORS = {
        TimeFrame.Days: 252,
        TimeFrame.Weeks: 52,
        TimeFrame.Months: 12,
        TimeFrame.Years: 1,
    }

    def __init__(self):
        # 使用 TimeReturn 来获取每个 timeframe 的 returns
        self.timereturn = TimeReturn(
            timeframe=self.p.timeframe, compression=self.p.compression, fund=self.p.fund
        )
        self.annual_vol = None
        self.std_period = None
        self.n_periods = 0
        self.factor = None

    def stop(self):
        # 取得所有周期性收益（字典 -> list）
        returns = list(itervalues(self.timereturn.get_analysis()))
        # returns 是按 period 排序的 simple returns (如 0.01, -0.02 ...)
        # 处理空情况
        if not returns:
            self.annual_vol = None
            self.std_period = None
            self.n_periods = 0
            self.rets = {"annual_vol": None}
            return

        # 如果需要，转换为对数收益 ln(1+r)
        rets = returns
        if self.p.use_log:
            try:
                rets = [math.log(1.0 + r) for r in returns]
            except Exception:
                # 若某些 r <= -1 导致 log 错误，回退为原始 returns 并记录
                rets = returns

        # 决定 factor（周期到年的换算因子）
        factor = None
        if self.p.factor is not None:
            factor = self.p.factor
        elif self.p.timeframe in self.RATEFACTORS:
            factor = self.RATEFACTORS[self.p.timeframe]

        self.factor = factor

        # 标准差（按用户是否要求样本修正）
        try:
            # backtrader 提供的 standarddev 支持 bessel 参数
            std_p = standarddev(rets, bessel=self.p.stddev_sample)
            # 如果 standarddev 返回 None 或异常，退回 numpy 实现
            if std_p is None:
                raise ValueError
        except Exception:
            std_p = float(np.std(rets, ddof=1 if self.p.stddev_sample else 0))

        self.std_period = float(std_p)
        self.n_periods = len(rets)

        # 年化：std_period * sqrt(factor) （如果不知道 factor，则不年化，返回周期 std）
        if factor is not None:
            try:
                self.annual_vol = float(self.std_period * math.sqrt(float(factor)))
            except Exception:
                self.annual_vol = None
        else:
            # 无 factor 时，返回 None 或者直接返回周期 std（此处返回周期 std）
            self.annual_vol = None

        # 保存分析结果，以便 get_analysis() 使用
        self.rets = {
            "annual_vol": self.annual_vol,
            "std_period": self.std_period,
            "n_periods": self.n_periods,
            "factor": self.factor,
            "timeframe": self.p.timeframe,
            "compression": self.p.compression,
            "use_log": self.p.use_log,
        }

    def get_analysis(self):
        return self.rets
