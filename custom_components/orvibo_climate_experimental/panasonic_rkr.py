"""Generate standalone Panasonic RKR (A75C4762) waveforms."""

from .control import OrviboInfrared

# Layout and timings: IRremoteESP8266, ir_Panasonic.h and ir_Panasonic.cpp.
_MODES = {"auto": 0, "dry": 2, "cool": 3, "heat": 4, "fan_only": 6}
_FAN_NIBBLES = {"min": 3, "low": 4, "medium": 5, "high": 6, "max": 7, "auto": 10}
_VERTICAL = {"highest": 1, "high": 2, "middle": 3, "low": 4, "lowest": 5, "auto": 15}
_HORIZONTAL = {"middle": 6, "far_left": 9, "left": 10, "right": 11, "far_right": 12, "auto": 13}


def panasonic_rkr_signal(
    *,
    power: bool,
    mode: str,
    temperature: int,
    fan: str = "auto",
    vertical: str = "middle",
    horizontal: str = "middle",
) -> OrviboInfrared:
    """Encode a 216-bit RKR state as two sections at 36.7 kHz."""
    if type(power) is not bool or type(temperature) is not int or not 16 <= temperature <= 30:
        raise ValueError("Expected a power flag and whole temperature from 16 to 30 C")
    try:
        operation = (_MODES[mode] << 4) | 0x08 | power
        fan_vane = (_FAN_NIBBLES[fan] << 4) | _VERTICAL[vertical]
        horizontal_vane = _HORIZONTAL[horizontal]
    except KeyError as err:
        raise ValueError("Unsupported Panasonic RKR mode, fan or vane setting") from err

    state = bytearray.fromhex(
        "02 20 E0 04 00 00 00 06 02 20 E0 04 00 08 00 80 00 00 00 0E E0 00 00 89 00 00 00"
    )
    state[13] = operation
    state[14] = (27 if mode == "fan_only" else temperature) << 1
    state[16] = fan_vane
    state[17] = horizontal_vane
    state[-1] = (0xF4 + sum(state[:-1])) & 0xFF

    pulses = []
    for section in (state[:8], state[8:]):
        if pulses:
            pulses.append(10000)
        pulses.extend((3456, 1728))
        for byte in section:
            for bit in range(8):
                pulses.extend((432, 1296 if byte & (1 << bit) else 432))
        pulses.append(432)
    return OrviboInfrared(36700, tuple(pulses))
