"""Encode the Hitachi AC264 state used by the RAR-2P2 family."""

from .control import OrviboInfrared

# Wire layout and timings: IRremoteESP8266, ir_Hitachi.h and ir_Hitachi.cpp.
_MODES = {"fan_only": 1, "cool": 3, "dry": 5, "heat": 6}
_FANS = {"low": 1, "medium": 3, "high": 4, "auto": 5}
_BUTTONS = {"power_mode": 0x13, "fan": 0x42, "temp_down": 0x43, "temp_up": 0x44}


def hitachi_264_signal(
    *, power: bool, mode: str, temperature: int, fan: str = "auto", button: str = "power_mode"
) -> OrviboInfrared:
    """Build an LSB-first 264-bit waveform with inverted byte pairs."""
    if type(power) is not bool or type(temperature) is not int or not 16 <= temperature <= 32:
        raise ValueError("Expected a power flag and whole temperature from 16 to 32 C")
    try:
        mode_code, fan_code, button_code = _MODES[mode], _FANS[fan], _BUTTONS[button]
    except KeyError as err:
        raise ValueError("Unsupported Hitachi AC264 mode, fan or button") from err

    state = bytearray(33)
    state[:4] = bytes.fromhex("01 10 00 40")
    state[5], state[7], state[9] = 0xFF, 0xCC, 0x92
    state[11] = button_code
    state[13] = (27 if mode == "fan_only" else temperature) << 2
    state[25] = (fan_code << 4) | mode_code
    state[27] = 0xD1 if power else 0xC1
    for index in range(3, len(state), 2):
        state[index + 1] = state[index] ^ 0xFF

    pulses = [3300, 1700]
    for byte in state:
        for bit in range(8):
            pulses.extend((400, 1250 if byte & (1 << bit) else 500))
    pulses.append(400)
    return OrviboInfrared(38000, tuple(pulses))
