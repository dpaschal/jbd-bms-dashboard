from __future__ import annotations
import sys
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar, QSystemTrayIcon, QMenu,
    QTabWidget,
)
from PyQt6.QtCore import QTimer, Qt, QEvent
from PyQt6.QtGui import QIcon, QMouseEvent
import serial.tools.list_ports


class ClickComboBox(QComboBox):
    """QComboBox that opens on click-release, stays open until item clicked.

    Fixes press-and-hold behavior on Fusion/Wayland where popup dismisses
    as soon as the mouse button is released.
    """
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if self.view().isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        e.accept()

from bms_monitor.config import load_settings, save_settings
from bms_monitor.protocol.parser import (
    make_read_request, make_fet_control_sequence, parse_response, ParseError,
)
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, BMSInfo
from bms_monitor.transport.serial import SerialTransport
from bms_monitor.transport.ble import BLETransport
from bms_monitor.storage.db import open_db, write_snapshot
from bms_monitor.alerts.checker import AlertChecker
from bms_monitor.ui.widgets.stats_row import StatsRow
from bms_monitor.ui.widgets.cells_widget import CellsWidget
from bms_monitor.ui.widgets.live_chart import LiveChart
from bms_monitor.ui.widgets.history_widget import HistoryWidget
from bms_monitor.ui.widgets.settings_panel import SettingsPanel
from bms_monitor.ui.widgets.alerts_banner import AlertsBanner

import sqlite3, os
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JBD BMS Monitor")
        self.setMinimumSize(900, 650)
        self._settings = load_settings()
        self._transport = None
        self._db: sqlite3.Connection | None = None
        self._last_basic: BasicInfo | None = None
        self._last_cells: CellVoltages | None = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._checker = AlertChecker(self._settings)
        self._checker.alert_triggered.connect(self._on_alert)
        self._build_ui()
        self._build_tray()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)
        root.addLayout(self._build_toolbar())
        self._alerts_banner = AlertsBanner()
        root.addWidget(self._alerts_banner)
        self._stats_row = StatsRow()
        self._stats_row.set_temp_unit(self._settings.get("temp_unit", "F"))
        root.addWidget(self._stats_row)
        middle = QHBoxLayout()
        self._cells_widget = CellsWidget()
        middle.addWidget(self._cells_widget, stretch=3)
        self._settings_panel = SettingsPanel(self._settings, self)
        self._settings_panel.setVisible(False)
        self._settings_panel.settings_saved.connect(self._on_settings_saved)
        from bms_monitor.ui.widgets.fets_flags import FetsFlagsWidget
        self._fets_flags = FetsFlagsWidget()
        self._fets_flags.fet_toggle_requested.connect(self._write_fet_state)
        middle.addWidget(self._fets_flags, stretch=1)
        root.addLayout(middle)
        self._tabs = QTabWidget()
        self._live_chart = LiveChart()
        self._history_widget = HistoryWidget()
        self._tabs.addTab(self._live_chart, "Live")
        self._tabs.addTab(self._history_widget, "History")
        root.addWidget(self._tabs)
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Disconnected")

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self._port_combo = ClickComboBox()
        self._port_combo.setMinimumWidth(160)
        self._port_combo.setMaxVisibleCount(12)
        # Force a scrollable popup with a visible scrollbar on Fusion —
        # Qt normally disables the scrollbar when the popup is sized by
        # item count.
        self._port_combo.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #e2e2e2;
                selection-background-color: #0f3460;
            }
            QComboBox QAbstractItemView QScrollBar:vertical {
                background: #16213e;
                width: 12px;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical {
                background: #4ecdc4;
                min-height: 20px;
                border-radius: 3px;
            }
        """)
        from PyQt6.QtWidgets import QListView
        self._port_combo.setView(QListView())
        self._port_combo.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._refresh_ports()
        bar.addWidget(QLabel("Port:"))
        bar.addWidget(self._port_combo)
        self._ble_btn = QPushButton("BLE Scan…")
        self._ble_btn.clicked.connect(self._ble_scan)
        bar.addWidget(self._ble_btn)
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        bar.addWidget(self._connect_btn)
        bar.addStretch()
        self._poll_combo = ClickComboBox()
        for label, secs in [("0.5s", 0.5), ("1s", 1.0), ("2s", 2.0), ("5s", 5.0)]:
            self._poll_combo.addItem(label, secs)
        self._poll_combo.setCurrentIndex(1)
        bar.addWidget(QLabel("Poll:"))
        bar.addWidget(self._poll_combo)
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self._toggle_settings)
        bar.addWidget(settings_btn)
        return bar

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("JBD BMS Monitor")
        menu = QMenu()
        menu.addAction("Show").triggered.connect(self.show)
        menu.addAction("Quit").triggered.connect(self.close)
        self._tray.setContextMenu(menu)
        self._tray.show()

    def _refresh_ports(self) -> None:
        self._port_combo.clear()
        for p in serial.tools.list_ports.comports():
            self._port_combo.addItem(p.device)
        self._port_combo.addItem("BLE (use scan)")

    def _toggle_connect(self) -> None:
        if self._transport is None:
            self._do_connect()
        else:
            self._do_disconnect()

    def _do_connect(self) -> None:
        target = self._port_combo.currentText()
        ble_address = self._port_combo.currentData()
        if ble_address:
            self._transport = BLETransport(self)
            target = ble_address
        elif target.startswith("BLE"):
            self._transport = BLETransport(self)
        else:
            self._transport = SerialTransport(self)
        self._transport.frame_received.connect(self._on_frame)
        self._transport.connection_changed.connect(self._on_connection_changed)
        self._transport.error_occurred.connect(self._on_error)
        self._transport.connect_device(target)
        if self._settings.get("log_enabled"):
            log_dir = os.path.expanduser(self._settings.get("log_dir", "~/.jbd-bms"))
            os.makedirs(log_dir, exist_ok=True)
            db_path = os.path.join(log_dir, f"bms_{datetime.now():%Y-%m-%d}.db")
            self._db = open_db(db_path)
            self._history_widget.set_db(self._db)
            self._status_bar.showMessage(f"Logging to {db_path}")
        interval_ms = int(self._poll_combo.currentData() * 1000)
        self._poll_timer.start(interval_ms)
        self._connect_btn.setText("Disconnect")
        QTimer.singleShot(500, self._poll_name)

    def _do_disconnect(self) -> None:
        self._poll_timer.stop()
        transport = self._transport
        self._transport = None
        if transport:
            try:
                transport.disconnect_device()
            except Exception:
                pass
        if self._db:
            self._db.close()
            self._db = None
        self._connect_btn.setText("Connect")

    def _ble_scan(self) -> None:
        from bms_monitor.ui.widgets.ble_scan_dialog import BLEScanDialog
        dlg = BLEScanDialog(self)
        if dlg.exec():
            address = dlg.selected_address()
            name = dlg.selected_name()
            label = f"BLE: {name} [{address}]"
            self._port_combo.addItem(label, address)
            self._port_combo.setCurrentText(label)

    def _poll(self) -> None:
        if self._transport:
            self._transport.send_frame(make_read_request(0x03))
            QTimer.singleShot(200, self._poll_cells)

    def _poll_cells(self) -> None:
        if self._transport:
            self._transport.send_frame(make_read_request(0x04))

    def _poll_name(self) -> None:
        if self._transport:
            self._transport.send_frame(make_read_request(0x05))

    def _on_frame(self, raw: bytes) -> None:
        try:
            result = parse_response(raw)
        except ParseError as e:
            reg = raw[1] if len(raw) > 1 else 0
            hex_dump = raw.hex() if len(raw) < 128 else raw[:128].hex() + "..."
            msg = f"Parse error reg=0x{reg:02x}: {e} | raw={hex_dump}"
            print(f"[BMS] {msg}", file=sys.stderr)
            self._status_bar.showMessage(msg[:200], 5000)
            return
        if isinstance(result, BasicInfo):
            self._last_basic = result
            self._stats_row.update(result)
            self._fets_flags.update(result)
            self._cells_widget.update_balance(result.balance_bitmask)
            self._live_chart.push_basic(result)
            if self._last_cells:
                self._checker.check(result, self._last_cells)
                if self._db:
                    write_snapshot(self._db, result, self._last_cells)
        elif isinstance(result, CellVoltages):
            self._last_cells = result
            self._cells_widget.update(result)
            self._stats_row.update_delta(result.delta * 1000)
        elif isinstance(result, BMSInfo):
            self.setWindowTitle(f"JBD BMS Monitor — {result.name}")

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self._status_bar.showMessage("Connected")
        else:
            self._do_disconnect()
            self._status_bar.showMessage("Disconnected")

    def _on_error(self, msg: str) -> None:
        self._status_bar.showMessage(f"Error: {msg}")

    def _on_alert(self, title: str, msg: str) -> None:
        self._alerts_banner.show_alert(title, msg)
        self._tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _toggle_settings(self) -> None:
        self._settings_panel.setVisible(not self._settings_panel.isVisible())
        if self._settings_panel.isVisible():
            self._settings_panel.show()

    def _on_settings_saved(self, new_settings: dict) -> None:
        self._settings = new_settings
        save_settings(new_settings)
        self._checker = AlertChecker(new_settings)
        self._checker.alert_triggered.connect(self._on_alert)
        self._stats_row.set_temp_unit(new_settings.get("temp_unit", "F"))
        if self._last_basic:
            self._stats_row.update(self._last_basic)

    def _write_fet_state(self, charge_on: bool, discharge_on: bool) -> None:
        if not self._transport:
            self._status_bar.showMessage("Not connected", 3000)
            return
        # Pause polling while factory-mode sequence runs.
        self._poll_timer.stop()
        frames = make_fet_control_sequence(charge_on, discharge_on)
        delay = 0
        for frame in frames:
            QTimer.singleShot(delay, lambda f=frame: self._transport.send_frame(f) if self._transport else None)
            delay += 250
        # Resume polling after factory-mode exit.
        QTimer.singleShot(delay + 300, self._resume_polling)
        target = []
        if charge_on: target.append("CHG")
        else:         target.append("chg")
        if discharge_on: target.append("DSG")
        else:            target.append("dsg")
        self._status_bar.showMessage(f"FET → {'/'.join(target)}", 4000)

    def _resume_polling(self) -> None:
        if self._transport:
            interval_ms = int(self._poll_combo.currentData() * 1000)
            self._poll_timer.start(interval_ms)
