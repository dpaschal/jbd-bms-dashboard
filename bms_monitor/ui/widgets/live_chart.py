from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
from bms_monitor.protocol.frames import BasicInfo
from collections import deque
import time

HISTORY = 300


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._plot = pg.PlotWidget(background="#16213e")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", "Voltage (V) / Current (A)")
        self._plot.setLabel("bottom", "Time (s)")
        self._plot.addLegend(offset=(60, 10))
        self._v_curve = self._plot.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._charge_curve = self._plot.plot(pen=pg.mkPen("#45b7d1", width=2), name="Charge (A)")
        self._discharge_curve = self._plot.plot(pen=pg.mkPen("#f5a623", width=2), name="Discharge (A)")
        self._power_curve = self._plot.plot(pen=pg.mkPen("#96ceb4", width=1, style=pg.QtCore.Qt.PenStyle.DashLine), name="Power (W/10)")
        layout.addWidget(self._plot)
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
        self._power.append(abs(info.pack_voltage * info.current) / 10.0)
        ts = list(self._times)
        self._v_curve.setData(ts, list(self._voltages))
        self._charge_curve.setData(ts, list(self._charge))
        self._discharge_curve.setData(ts, list(self._discharge))
        self._power_curve.setData(ts, list(self._power))
