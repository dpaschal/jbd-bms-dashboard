from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
import pyqtgraph as pg
import sqlite3
from bms_monitor.storage.db import query_snapshots, export_csv
import time


class HistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self._btn_1h = QPushButton("Last 1h"); self._btn_1h.clicked.connect(lambda: self._load(3600))
        self._btn_6h = QPushButton("Last 6h"); self._btn_6h.clicked.connect(lambda: self._load(21600))
        self._btn_24h = QPushButton("Last 24h"); self._btn_24h.clicked.connect(lambda: self._load(86400))
        self._btn_export = QPushButton("Export CSV"); self._btn_export.clicked.connect(self._export)
        for btn in (self._btn_1h, self._btn_6h, self._btn_24h, self._btn_export):
            controls.addWidget(btn)
        controls.addStretch()
        layout.addLayout(controls)
        self._plot = pg.PlotWidget(background="#16213e")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._v_curve = self._plot.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._soc_curve = self._plot.plot(pen=pg.mkPen("#45b7d1", width=1), name="SOC")
        layout.addWidget(self._plot)
        self._conn: sqlite3.Connection | None = None

    def set_db(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _load(self, seconds: int) -> None:
        if not self._conn:
            return
        now = time.time()
        rows = query_snapshots(self._conn, now - seconds, now)
        if not rows:
            return
        ts = [r["ts"] - rows[0]["ts"] for r in rows]
        vs = [r["pack_voltage"] for r in rows]
        socs = [r["soc"] for r in rows]
        self._v_curve.setData(ts, vs)
        self._soc_curve.setData(ts, socs)

    def _export(self) -> None:
        if not self._conn:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if path:
            export_csv(self._conn, path)
