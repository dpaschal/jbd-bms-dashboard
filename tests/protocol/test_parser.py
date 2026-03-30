import struct
import pytest
from bms_monitor.protocol.parser import (
    make_read_request, parse_response, ParseError,
)
from bms_monitor.protocol.frames import BasicInfo, CellVoltages

REG_BASIC = 0x03
REG_CELLS = 0x04
REG_INFO  = 0x05


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def _wrap(reg: int, data: bytes) -> bytes:
    status = 0x00
    header = bytes([status, len(data)])
    cs = _checksum(header + data)
    return bytes([0xDD, reg, status, len(data)]) + data + cs + bytes([0x77])


def _basic_info_data(
    pack_mv: int = 5120, current_ma: int = 1240,
    soc: int = 83, cell_count: int = 4, temp_count: int = 1,
) -> bytes:
    data = struct.pack(
        '>HhHHHHHHH',
        pack_mv, current_ma,
        8300, 10000, 42, 0x0000, 0x0000, 0x0000, 0x0000,
    )
    data += bytes([0x20, soc, 0x03, cell_count, temp_count])
    for _ in range(temp_count):
        data += struct.pack('>H', 2981)
    return data


def test_make_read_request_basic_info():
    req = make_read_request(REG_BASIC)
    assert req == bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])


def test_make_read_request_cells():
    req = make_read_request(REG_CELLS)
    assert req[0] == 0xDD
    assert req[2] == 0x04
    assert req[-1] == 0x77


def test_parse_basic_info():
    frame = _wrap(REG_BASIC, _basic_info_data())
    result = parse_response(frame)
    assert isinstance(result, BasicInfo)
    assert result.pack_voltage == pytest.approx(51.2, abs=0.01)
    assert result.current == pytest.approx(12.4, abs=0.01)
    assert result.soc == 83
    assert result.charge_fet is True
    assert result.discharge_fet is True
    assert len(result.temps) == 1
    assert result.temps[0] == pytest.approx(25.0, abs=0.1)


def test_parse_cell_voltages():
    voltages_mv = [3210, 3200, 3215, 3090]
    data = b"".join(struct.pack(">H", v) for v in voltages_mv)
    frame = _wrap(REG_CELLS, data)
    result = parse_response(frame)
    assert isinstance(result, CellVoltages)
    assert result.voltages[3] == pytest.approx(3.090, abs=0.001)
    assert result.delta == pytest.approx(0.125, abs=0.001)


def test_bad_checksum_raises():
    frame = bytearray(_wrap(REG_BASIC, _basic_info_data()))
    frame[-3] ^= 0xFF
    with pytest.raises(ParseError):
        parse_response(bytes(frame))


def test_bad_start_byte_raises():
    frame = bytearray(_wrap(REG_BASIC, _basic_info_data()))
    frame[0] = 0xAA
    with pytest.raises(ParseError):
        parse_response(bytes(frame))
