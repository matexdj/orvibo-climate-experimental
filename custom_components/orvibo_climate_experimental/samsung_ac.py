"""Encode Samsung air-conditioner state and power-transition signals."""

from .control import OrviboInfrared

# Wire layout and timings: IRremoteESP8266, ir_Samsung.h and ir_Samsung.cpp.
_MODES = {"auto": 0, "cool": 1, "dry": 2, "fan_only": 3, "heat": 4}
_FANS = {"auto": 0, "low": 2, "medium": 4, "high": 5}
_SWING = {"off": 7, "vertical": 2, "horizontal": 3, "both": 4}


def samsung_ac_signal(
    *,
    power: bool,
    mode: str,
    temperature: int,
    fan: str = "auto",
    swing: str = "off",
    extended: bool = True,
) -> OrviboInfrared:
    """Use the extended frame for power transitions and the short frame for updates."""
    if type(power) is not bool or type(temperature) is not int or not 16 <= temperature <= 30:
        raise ValueError("Expected a power flag and whole temperature from 16 to 30 C")
    if mode == "auto" and fan != "auto":
        raise ValueError("Samsung automatic mode requires automatic fan")
    try:
        mode_code = _MODES[mode]
        fan_code = 6 if mode == "auto" else _FANS[fan]
        swing_code = _SWING[swing]
    except KeyError as err:
        raise ValueError("Unsupported Samsung mode, fan or swing") from err

    power_byte = 0xF0 if power else 0xC0
    first = bytearray((0x02, 0x02, 0, 0, 0, 0, power_byte))
    last = bytearray((
        0x01, 0x02, 0x80 | (swing_code << 4), 0x71,
        (temperature - 16) << 4, 1 | (mode_code << 4) | (fan_code << 1), power_byte,
    ))
    sections = [first]
    if extended:
        sections.append(bytearray.fromhex("01 D2 0F 00 00 00 00"))
    sections.append(last)

    pulses = [690, 17844]
    for index, section in enumerate(sections):
        ones = section[0].bit_count() + (section[1] & 0x0F).bit_count()
        ones += (section[2] >> 4).bit_count() + sum(byte.bit_count() for byte in section[3:])
        check = ones ^ 0xFF
        section[1] = (section[1] & 0x0F) | ((check & 0x0F) << 4)
        section[2] = (section[2] & 0xF0) | (check >> 4)
        if index:
            pulses.append(2886)
        pulses.extend((3086, 8864))
        for byte in section:
            for bit in range(8):
                pulses.extend((586, 1432 if byte & (1 << bit) else 436))
        pulses.append(586)
    return OrviboInfrared(38000, tuple(pulses))
