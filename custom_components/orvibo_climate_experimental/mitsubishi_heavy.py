"""Generate standalone Mitsubishi Heavy Industries 88- and 152-bit signals."""

from .control import OrviboInfrared

# Wire fields and pulse timings documented by IRremoteESP8266:
# https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_MitsubishiHeavy.h
# https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_MitsubishiHeavy.cpp
_MODES = {"auto": 0, "cool": 1, "dry": 2, "fan_only": 3, "heat": 4}
_FANS_88 = {"auto": 0, "low": 2, "medium": 3, "high": 4}
_FANS_152 = {"auto": 0, "low": 1, "medium": 2, "high": 3, "max": 4}
_VERTICAL_88 = {"off": 0, "auto": 4, "middle": 3}
_VERTICAL_152 = {"off": 6, "auto": 0, "middle": 3}
_HORIZONTAL_88 = {"off": 0, "auto": 8, "sweep": 6}
_HORIZONTAL_152 = {"off": 8, "auto": 0, "sweep": 7}


def mitsubishi_heavy_signal(
    *,
    bits: int,
    power: bool,
    mode: str,
    temperature: int,
    fan: str = "auto",
    vertical: str = "off",
    horizontal: str = "off",
) -> OrviboInfrared:
    """Encode one full state for an explicitly selected protocol variant."""
    if type(bits) is not int or bits not in (88, 152):
        raise ValueError("Expected the 88- or 152-bit Mitsubishi Heavy variant")
    if type(power) is not bool or type(temperature) is not int or not 17 <= temperature <= 31:
        raise ValueError("Expected a power flag and whole temperature from 17 to 31 C")
    short = bits == 88
    try:
        operation = _MODES[mode] | (0x08 if power else 0)
        fan_code = (_FANS_88 if short else _FANS_152)[fan]
        vane_v = (_VERTICAL_88 if short else _VERTICAL_152)[vertical]
        vane_h = (_HORIZONTAL_88 if short else _HORIZONTAL_152)[horizontal]
    except KeyError as err:
        raise ValueError("Unsupported Mitsubishi Heavy mode, fan or vane setting") from err

    payload = bytearray(bits // 8)
    payload[:3] = bytes.fromhex("AD 51 3C")
    if short:
        payload[3] = 0xD9
        payload[5] = ((vane_v & 1) << 1) | ((vane_h & 3) << 2) | ((vane_h >> 2) << 6)
        payload[7] = ((vane_v >> 1) << 3) | (fan_code << 5)
        payload[9] = ((temperature - 17) << 4) | operation
    else:
        payload[3] = 0xE5
        payload[5] = operation
        payload[7] = temperature - 17
        payload[9] = fan_code
        payload[11] = vane_v << 5
        payload[13] = vane_h
        payload[17] = 0x80
    for index in range(3, len(payload), 2):
        payload[index + 1] = payload[index] ^ 0xFF

    frame = [3140, 1630]
    for byte in payload:
        for bit in range(8):
            frame.extend((370, 420 if byte & (1 << bit) else 1220))
    frame.append(370)
    return OrviboInfrared(38000, tuple(frame))
