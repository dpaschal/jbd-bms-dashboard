from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer


class AlertsBanner(QWidget):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setStyleSheet("background: #e94560; border-radius: 4px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self._label = QLabel()
        self._label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self._label)
        layout.addStretch()
        dismiss = QPushButton("✕")
        dismiss.setFlat(True)
        dismiss.setStyleSheet("color: white;")
        dismiss.clicked.connect(lambda: self.setVisible(False))
        layout.addWidget(dismiss)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self.setVisible(False))

    def show_alert(self, title: str, msg: str) -> None:
        self._label.setText(f"⚠ {title}: {msg}")
        self.setVisible(True)
        self._timer.start(10_000)
