from __future__ import annotations
import struct
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, BMSInfo, ProtectionFlags


class ParseError(Exception):
    pass


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def make_read_request(register: int) -> bytes:
    payload = bytes([register, 0x00])
    cs = _checksum(payload)
    return bytes([0xDD, 0xA5, register, 0x00]) + cs + bytes([0x77])


def make_write_request(register: int, data: bytes) -> bytes:
    """JBD write command. Frame: DD 5A <reg> <len> <data...> <cs:2> 77.

    Checksum covers reg + len + data, same formula as read responses.
    """
    length = len(data)
    cs = _checksum(bytes([register, length]) + data)
    return bytes([0xDD, 0x5A, register, length]) + data + cs + bytes([0x77])


# Factory-mode magic values for JBD FET control.
FACTORY_UNLOCK = 0x5678
FACTORY_LOCK   = 0x2828
REG_FACTORY    = 0x00
REG_FET_CTRL   = 0xE1


def make_fet_control_sequence(charge_on: bool, discharge_on: bool) -> list[bytes]:
    """Build the 3-frame sequence that toggles the FETs.

    JBD requires entering factory mode (reg 0x00 = 0x5678), writing the
    FET state to reg 0xE1 (bit0 = discharge off, bit1 = charge off —
    both zero means both ON), then exiting factory mode (reg 0x00 = 0x2828).
    """
    mask = 0x00
    if not discharge_on:
        mask |= 0x01
    if not charge_on:
        mask |= 0x02
    unlock = make_write_request(REG_FACTORY, FACTORY_UNLOCK.to_bytes(2, "big"))
    set_fet = make_write_request(REG_FET_CTRL, bytes([0x00, mask]))
    lock = make_write_request(REG_FACTORY, FACTORY_LOCK.to_bytes(2, "big"))
    return [unlock, set_fet, lock]


def parse_response(data: bytes) -> BasicInfo | CellVoltages | BMSInfo:
    if len(data) < 7:
        raise ParseError("frame too short")
    if data[0] != 0xDD:
        raise ParseError(f"bad start byte: {data[0]:#x}")
    if data[-1] != 0x77:
        raise ParseError(f"bad end byte: {data[-1]:#x}")

    reg = data[1]
    status = data[2]
    length = data[3]
    payload = data[4: 4 + length]
    cs_received = data[4 + length: 4 + length + 2]
    cs_expected = _checksum(bytes([status, length]) + payload)

    if cs_received != cs_expected:
        raise ParseError(
            f"checksum mismatch: got {cs_received.hex()}, expected {cs_expected.hex()}"
        )
    if status != 0x00:
        raise ParseError(f"BMS reported error status: {status:#x}")

    if reg == 0x03:
        return _parse_basic_info(payload)
    if reg == 0x04:
        return _parse_cell_voltages(payload)
    if reg == 0x05:
        return _parse_bms_info(payload)
    raise ParseError(f"unknown register: {reg:#x}")


def _parse_basic_info(data: bytes) -> BasicInfo:
    if len(data) < 23:
        raise ParseError("BasicInfo payload too short")
    (
        pack_mv, current_ma, remaining, nominal,
        cycles, _prod_date, bal_low, bal_high, prot_mask,
    ) = struct.unpack_from(">HhHHHHHHH", data, 0)
    bal_mask = (bal_high << 16) | bal_low

    sw_ver, soc, fet, cell_count, temp_count = struct.unpack_from(">BBBBB", data, 18)
    temps = []
    for i in range(temp_count):
        raw, = struct.unpack_from(">H", data, 23 + i * 2)
        temps.append((raw - 2731) / 10.0)

    return BasicInfo(
        pack_voltage=pack_mv / 100.0,
        current=current_ma / 100.0,
        remaining_ah=remaining / 100.0,
        nominal_ah=nominal / 100.0,
        cycles=cycles,
        soc=soc,
        charge_fet=bool(fet & 0x01),
        discharge_fet=bool(fet & 0x02),
        cell_count=cell_count,
        temp_count=temp_count,
        temps=temps,
        protection=ProtectionFlags.from_bitmask(prot_mask),
        balance_bitmask=bal_mask,
    )


def _parse_cell_voltages(data: bytes) -> CellVoltages:
    count = len(data) // 2
    voltages = [
        struct.unpack_from(">H", data, i * 2)[0] / 1000.0
        for i in range(count)
    ]
    return CellVoltages(voltages=voltages)


def _parse_bms_info(data: bytes) -> BMSInfo:
    return BMSInfo(name=data.decode("ascii", errors="replace").strip())
