from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
import pyqtgraph as pg
from bms_monitor.protocol.frames import BasicInfo
from collections import deque
import time

HISTORY = 300
BG = "#16213e"


class _Stat(QLabel):
    """Small inline stat label (e.g. 'now 13.36V  min 13.10  max 13.42')."""
    def __init__(self):
        super().__init__("--")
        self.setStyleSheet("color: #cfd8dc; font-size: 9px;")


def _plot(title: str, ylabel: str) -> pg.PlotWidget:
    p = pg.PlotWidget(background=BG)
    p.showGrid(x=True, y=True, alpha=0.2)
    p.setLabel("left", ylabel)
    p.setLabel("bottom", "")
    p.addLegend(offset=(60, 4))
    p.setMinimumHeight(110)
    return p


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self._plot_v = _plot("Pack Voltage", "V")
        self._v_curve = self._plot_v.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._stat_v = _Stat()
        layout.addWidget(self._build_row("Voltage", self._plot_v, self._stat_v))

        self._plot_chg = _plot("Charge (in)", "A")
        self._charge_curve = self._plot_chg.plot(pen=pg.mkPen("#45b7d1", width=2), name="Charge (A)")
        self._stat_chg = _Stat()
        layout.addWidget(self._build_row("Charge", self._plot_chg, self._stat_chg))

        self._plot_dsg = _plot("Discharge (out)", "A / W")
        self._discharge_curve = self._plot_dsg.plot(pen=pg.mkPen("#f5a623", width=2), name="Discharge (A)")
        self._power_curve = self._plot_dsg.plot(
            pen=pg.mkPen("#96ceb4", width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            name="Power (W)",
        )
        self._stat_dsg = _Stat()
        layout.addWidget(self._build_row("Discharge", self._plot_dsg, self._stat_dsg))

        self._plot_chg.setXLink(self._plot_v)
        self._plot_dsg.setXLink(self._plot_v)

        self._times: deque[float] = deque(maxlen=HISTORY)
        self._voltages: deque[float] = deque(maxlen=HISTORY)
        self._charge: deque[float] = deque(maxlen=HISTORY)
        self._discharge: deque[float] = deque(maxlen=HISTORY)
        self._power: deque[float] = deque(maxlen=HISTORY)
        self._t0 = time.monotonic()

    def _build_row(self, name: str, plot: pg.PlotWidget, stat: QLabel) -> QWidget:
        host = QWidget()
        v = QVBoxLayout(host)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(plot)
        v.addWidget(stat)
        return host

    def push_basic(self, info: BasicInfo) -> None:
        t = time.monotonic() - self._t0
        self._times.append(t)
        self._voltages.append(info.pack_voltage)
        chg = info.current if info.current > 0 else 0
        dsg = abs(info.current) if info.current < 0 else 0
        pwr = abs(info.pack_voltage * info.current) if info.current < 0 else 0
        self._charge.append(chg)
        self._discharge.append(dsg)
        self._power.append(pwr)

        ts = list(self._times)
        self._v_curve.setData(ts, list(self._voltages))
        self._charge_curve.setData(ts, list(self._charge))
        self._discharge_curve.setData(ts, list(self._discharge))
        self._power_curve.setData(ts, list(self._power))

        vs = list(self._voltages)
        cs = list(self._charge)
        ds = list(self._discharge)
        ps = list(self._power)
        self._stat_v.setText(
            f"now {vs[-1]:.2f}V   min {min(vs):.2f}   max {max(vs):.2f}"
        )
        self._stat_chg.setText(
            f"now {chg:.2f}A   peak {max(cs):.2f}A"
        )
        self._stat_dsg.setText(
            f"now {dsg:.2f}A / {pwr:.1f}W   peak {max(ds):.2f}A / {max(ps):.1f}W"
        )
