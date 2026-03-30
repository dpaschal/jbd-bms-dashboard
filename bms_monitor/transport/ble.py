from __future__ import annotations
import asyncio
import threading
from bleak import BleakClient, BleakScanner
from bms_monitor.transport.base import Transport

BLE_SERVICE_UUID  = "0000ff00-0000-1000-8000-00805f9b34fb"
BLE_TX_CHAR_UUID  = "0000ff01-0000-1000-8000-00805f9b34fb"
BLE_RX_CHAR_UUID  = "0000ff02-0000-1000-8000-00805f9b34fb"


class BLETransport(Transport):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: BleakClient | None = None
        self._buf = bytearray()

    def connect_device(self, target: str) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, args=(target,), daemon=True
        )
        self._thread.start()

    def disconnect_device(self) -> None:
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)

    def send_frame(self, data: bytes) -> None:
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(
                self._client.write_gatt_char(BLE_RX_CHAR_UUID, data, response=False),
                self._loop,
            )

    def _run_loop(self, target: str) -> None:
        self._loop.run_until_complete(self._connect_and_run(target))

    async def _connect_and_run(self, target: str) -> None:
        address = await self._resolve_address(target)
        if not address:
            self._emit_error(f"BLE device not found: {target!r}")
            return
        try:
            async with BleakClient(address) as client:
                self._client = client
                await client.start_notify(BLE_TX_CHAR_UUID, self._on_notify)
                self._emit_connected(True)
                while client.is_connected:
                    await asyncio.sleep(0.5)
        except Exception as e:
            self._emit_error(str(e))
        finally:
            self._emit_connected(False)

    async def _resolve_address(self, target: str) -> str | None:
        if ":" in target or "-" in target:
            return target
        devices = await BleakScanner.discover(timeout=5.0)
        for d in devices:
            if target.lower() in (d.name or "").lower():
                return d.address
        return None

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        self._buf.extend(data)
        while True:
            start = self._buf.find(0xDD)
            if start == -1:
                self._buf.clear()
                break
            if start > 0:
                del self._buf[:start]
            end = self._buf.find(0x77, 4)
            if end == -1:
                break
            frame = bytes(self._buf[: end + 1])
            del self._buf[: end + 1]
            self._emit_frame(frame)

    def _emit_frame(self, frame: bytes) -> None:
        self.frame_received.emit(frame)

    def _emit_connected(self, state: bool) -> None:
        self.connection_changed.emit(state)

    def _emit_error(self, msg: str) -> None:
        self.error_occurred.emit(msg)
