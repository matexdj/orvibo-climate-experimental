"""Generate standalone Mitsubishi Electric MITSUBISHI_AC waveforms."""

from .control import OrviboInfrared

# Wire fields and timing reference:
# https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Mitsubishi.h
# https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Mitsubishi.cpp
_MODE_BYTES = {
    "heat": (0x08, 0x30),
    "dry": (0x10, 0x32),
    "cool": (0x18, 0x36),
    "auto": (0x20, 0x30),
    "fan_only": (0x38, 0x37),
}
_FAN_BITS = {"auto": 0x80, "low": 1, "medium": 2, "high": 3, "max": 4, "quiet": 5}
_VANE_BITS = {"auto": 0, "middle": 3 << 3, "swing": 7 << 3}


def mitsubishi_144_signal(
    *,
    power: bool,
    mode: str,
    temperature: int,
    fan: str = "auto",
    vane: str = "auto",
) -> OrviboInfrared:
    """Encode a complete state as two identical 144-bit frames at 38 kHz."""
    if type(power) is not bool or type(temperature) is not int or not 16 <= temperature <= 31:
        raise ValueError("Expected a power flag and whole temperature from 16 to 31 C")
    try:
        mode_bits, vane_defaults = _MODE_BYTES[mode]
        fan_vane = 0x40 | _FAN_BITS[fan] | _VANE_BITS[vane]
    except KeyError as err:
        raise ValueError("Unsupported Mitsubishi mode, fan or vane setting") from err

    payload = bytearray(18)
    payload[:5] = bytes.fromhex("23 CB 26 01 00")
    payload[5] = 0x20 if power else 0
    payload[6:10] = bytes((mode_bits, temperature - 16, vane_defaults, fan_vane))
    payload[-1] = sum(payload[:-1]) & 0xFF

    frame = [3400, 1750]
    for byte in payload:
        for bit in range(8):
            frame.extend((450, 1300 if byte & (1 << bit) else 420))
    frame.extend((440, 15500))
    return OrviboInfrared(38000, tuple(frame) * 2)
