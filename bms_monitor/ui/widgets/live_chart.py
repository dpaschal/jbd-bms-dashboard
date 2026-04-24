from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
from bms_monitor.protocol.frames import BasicInfo
from collections import deque
import time

HISTORY = 300
BG = "#16213e"


def _plot(title: str, ylabel: str, height: int = 140) -> pg.PlotWidget:
    p = pg.PlotWidget(background=BG)
    p.showGrid(x=True, y=True, alpha=0.2)
    p.setLabel("left", ylabel)
    p.setTitle(title, color="#cfd8dc", size="9pt")
    p.addLegend(offset=(60, 6))
    p.setMinimumHeight(height)
    return p


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._plot_v = _plot("Pack Voltage", "V")
        self._v_curve = self._plot_v.plot(
            pen=pg.mkPen("#4ecdc4", width=2), name="Voltage"
        )

        self._plot_chg = _plot("Charge Current (in)", "A")
        self._charge_curve = self._plot_chg.plot(
            pen=pg.mkPen("#45b7d1", width=2), name="Charge (A)"
        )

        self._plot_dsg = _plot("Discharge Current + Power (out)", "A / W")
        self._discharge_curve = self._plot_dsg.plot(
            pen=pg.mkPen("#f5a623", width=2), name="Discharge (A)"
        )
        self._power_curve = self._plot_dsg.plot(
            pen=pg.mkPen("#96ceb4", width=1,
                         style=pg.QtCore.Qt.PenStyle.DashLine),
            name="Power (W)",
        )

        for p in (self._plot_v, self._plot_chg, self._plot_dsg):
            p.setLabel("bottom", "Time (s)")
            layout.addWidget(p)

        # X axes share range so all three scroll together.
        self._plot_chg.setXLink(self._plot_v)
        self._plot_dsg.setXLink(self._plot_v)

        self._times: deque[float] = deque(maxlen=HISTORY)
        self._voltages: deque[float] = deque(maxlen=HISTORY)
        self._charge: deque[float] = deque(maxlen=HISTORY)
        self._discharge: deque[float] = deque(maxlen=HISTORY)
        self._power: deque[float] = deque(maxlen=HISTORY)
        self._t0 = time.monotonic()

    def push_basic(self, info: BasicInfo) -> None:
        t = time.monotonic() - self._t0
        self._times.append(t)
        self._voltages.append(info.pack_voltage)
        self._charge.append(info.current if info.current > 0 else 0)
        self._discharge.append(abs(info.current) if info.current < 0 else 0)
        # Power (W) — absolute output power; shown on discharge chart.
        self._power.append(abs(info.pack_voltage * info.current) if info.current < 0 else 0)
        ts = list(self._times)
        self._v_curve.setData(ts, list(self._voltages))
        self._charge_curve.setData(ts, list(self._charge))
        self._discharge_curve.setData(ts, list(self._discharge))
        self._power_curve.setData(ts, list(self._power))
