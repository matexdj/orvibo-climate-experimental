"""Offline regression tests for the AC profile and Home Assistant command path."""

import asyncio
from dataclasses import replace
from enum import IntFlag, StrEnum
import hashlib
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import AsyncMock, Mock, patch


PACKAGE = "_orvibo_ac_tests"
package = ModuleType(PACKAGE)
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components/orvibo_climate_experimental")
]
sys.modules[PACKAGE] = package
protocol = importlib.import_module(f"{PACKAGE}.protocol")
profiles = importlib.import_module(f"{PACKAGE}.ac_profiles")
mitsubishi = importlib.import_module(f"{PACKAGE}.mitsubishi_144")
mitsubishi_heavy = importlib.import_module(f"{PACKAGE}.mitsubishi_heavy")
panasonic = importlib.import_module(f"{PACKAGE}.panasonic_rkr")
hitachi = importlib.import_module(f"{PACKAGE}.hitachi_264")
samsung = importlib.import_module(f"{PACKAGE}.samsung_ac")
binary = importlib.import_module(f"{PACKAGE}.binary")


class HVACMode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class Features(IntFlag):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 8
    SWING_MODE = 32
    PRESET_MODE = 16
    TURN_OFF = 128
    TURN_ON = 256


class HomeAssistantError(Exception):
    pass


class DeviceEntity:
    def __init__(self, coordinator, device_id):
        self.coordinator = coordinator
        self._device_id = device_id
        self.async_write_ha_state = Mock()

    @property
    def _device(self):
        return next(
            (d for d in self.coordinator.data.devices if d.uid == self._device_id), None
        )

    @property
    def available(self):
        return self.coordinator.last_update_success


with patch.dict(sys.modules, {
    "homeassistant": ModuleType("homeassistant"),
    "homeassistant.components.climate": SimpleNamespace(
        ClimateEntity=object, ClimateEntityFeature=Features, HVACMode=HVACMode
    ),
    "homeassistant.config_entries": SimpleNamespace(ConfigEntry=object),
    "homeassistant.const": SimpleNamespace(UnitOfTemperature=SimpleNamespace(CELSIUS="°C")),
    "homeassistant.core": SimpleNamespace(HomeAssistant=object),
    "homeassistant.exceptions": SimpleNamespace(HomeAssistantError=HomeAssistantError),
    "homeassistant.helpers.entity_platform": SimpleNamespace(AddEntitiesCallback=object),
    f"{PACKAGE}.const": SimpleNamespace(
        DOMAIN="orvibo_climate_experimental", CONF_FAMILY_ID="family_id", CONF_HOST="host"
    ),
    f"{PACKAGE}.coordinator": SimpleNamespace(OrviboCloudCoordinator=object),
    f"{PACKAGE}.entity": SimpleNamespace(OrviboCloudDeviceEntity=DeviceEntity),
}):
    climate = importlib.import_module(f"{PACKAGE}.climate")
    backend = importlib.import_module(f"{PACKAGE}.ac_backend")


AC_ROW = {
    "deviceId": "virtual-ac",
    "uid": "hardware",
    "model": "hub-model",
    "deviceType": 5,
    "subDeviceType": 2,
    "irDeviceId": 10502,
}
HUB_ROW = {
    "deviceId": "hub", "uid": "hardware", "model": "hub-model", "deviceType": 67
}


def devices(*rows):
    return protocol.parse_readtable_devices({"data": {"device": list(rows)}})


class ProfileTests(unittest.TestCase):
    def test_hitachi_264_matches_published_off_state(self):
        signal = hitachi.hitachi_264_signal(power=False, mode="heat", temperature=25)
        self.assertEqual(signal.frequency, 38000)
        self.assertEqual(signal.pulses[:2], (3300, 1700))
        self.assertEqual(len(signal.pulses), 531)
        spaces = signal.pulses[3:-1:2]
        decoded = bytes(
            sum((space == 1250) << bit for bit, space in enumerate(spaces[offset:offset + 8]))
            for offset in range(0, len(spaces), 8)
        )
        self.assertEqual(decoded, bytes.fromhex(
            "01 10 00 40 BF FF 00 CC 33 92 6D 13 EC 64 9B 00 FF 00 FF 00 "
            "FF 00 FF 00 FF 56 A9 C1 3E 00 FF 00 FF"
        ))

    def test_samsung_ac_matches_published_off_capture(self):
        settings = {"power": False, "mode": "cool", "temperature": 24,
                    "fan": "low", "swing": "vertical"}
        signal = samsung.samsung_ac_signal(**settings)
        self.assertEqual(signal.frequency, 38000)
        self.assertEqual(len(signal.pulses), 349)
        self.assertEqual(signal.pulses[:4], (690, 17844, 3086, 8864))
        self.assertEqual(signal.pulses[116:120], (586, 2886, 3086, 8864))
        spaces = tuple(
            space
            for start in (2, 118, 234)
            for space in signal.pulses[start + 3:start + 114:2]
        )
        decoded = bytes(
            sum((space == 1432) << bit for bit, space in enumerate(spaces[offset:offset + 8]))
            for offset in range(0, len(spaces), 8)
        )
        self.assertEqual(decoded, bytes.fromhex(
            "02 B2 0F 00 00 00 C0 01 D2 0F 00 00 00 00 01 12 AF 71 80 15 C0"
        ))
        short = samsung.samsung_ac_signal(**settings, extended=False)
        self.assertEqual(short.pulses, signal.pulses[:118] + signal.pulses[234:])

    def test_panasonic_rkr_uses_two_sections_and_full_state(self):
        signal = panasonic.panasonic_rkr_signal(
            power=True, mode="cool", temperature=24, fan="medium",
            vertical="auto", horizontal="left",
        )
        self.assertEqual(signal.frequency, 36700)
        self.assertEqual(len(signal.pulses), 439)
        self.assertEqual(signal.pulses[130:134], (432, 10000, 3456, 1728))
        spaces = signal.pulses[3:130:2] + signal.pulses[135:-1:2]
        decoded = bytes(
            sum((space == 1296) << bit for bit, space in enumerate(spaces[offset:offset + 8]))
            for offset in range(0, len(spaces), 8)
        )
        self.assertEqual(decoded[:8], bytes.fromhex("02 20 E0 04 00 00 00 06"))
        self.assertEqual(decoded[13:18], bytes.fromhex("39 30 80 5F 0A"))
        self.assertEqual(decoded[23], 0x89)
        self.assertEqual(decoded[-1], 0xCF)

    def test_panasonic_rkr_rejects_unsupported_settings(self):
        settings = {"power": False, "mode": "heat", "temperature": 22}
        for invalid in ({"temperature": 31}, {"fan": "quiet"}, {"horizontal": "off"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                panasonic.panasonic_rkr_signal(**{**settings, **invalid})

    def test_mitsubishi_heavy_matches_reference_frames(self):
        samples = (
            (88, {"power": True, "mode": "dry", "temperature": 25, "horizontal": "sweep"},
             "AD 51 3C D9 26 48 B7 00 FF 8A 75"),
            (152, {"power": False, "mode": "heat", "temperature": 24,
                   "fan": "max", "vertical": "auto", "horizontal": "auto"},
             "AD 51 3C E5 1A 04 FB 07 F8 04 FB 00 FF 00 FF 00 FF 80 7F"),
        )
        for bits, settings, expected in samples:
            with self.subTest(bits=bits):
                signal = mitsubishi_heavy.mitsubishi_heavy_signal(bits=bits, **settings)
                self.assertEqual(signal.frequency, 38000)
                self.assertEqual(len(signal.pulses), 2 * bits + 3)
                self.assertEqual(signal.pulses[:2], (3140, 1630))
                self.assertTrue(all(mark == 370 for mark in signal.pulses[2::2]))
                spaces = signal.pulses[3::2]
                self.assertEqual(set(spaces), {420, 1220})
                decoded = bytes(
                    sum((space == 420) << bit for bit, space in enumerate(spaces[offset:offset + 8]))
                    for offset in range(0, len(spaces), 8)
                )
                self.assertEqual(decoded, bytes.fromhex(expected))

    def test_mitsubishi_heavy_rejects_unsupported_variant_and_settings(self):
        settings = {"bits": 88, "power": True, "mode": "heat", "temperature": 22}
        for invalid in ({"bits": 144}, {"temperature": 16}, {"fan": "max"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                mitsubishi_heavy.mitsubishi_heavy_signal(**{**settings, **invalid})

    def test_mitsubishi_144_matches_published_off_capture(self):
        signal = mitsubishi.mitsubishi_144_signal(
            power=False, mode="cool", temperature=26, fan="low", vane="swing"
        )
        self.assertEqual(signal.frequency, 38000)
        self.assertEqual(len(signal.pulses), 584)
        frame = signal.pulses[:292]
        self.assertEqual(signal.pulses[292:], frame)
        self.assertEqual(frame[:2], (3400, 1750))
        self.assertEqual(frame[-2:], (440, 15500))
        spaces = frame[3:-2:2]
        decoded = bytes(
            sum((space == 1300) << bit for bit, space in enumerate(spaces[offset:offset + 8]))
            for offset in range(0, len(spaces), 8)
        )
        # Expected bytes decoded from the upstream hardware capture.
        self.assertEqual(decoded, bytes.fromhex("23 CB 26 01 00 00 18 0A 36 79 00 00 00 00 00 00 00 E6"))

    def test_mitsubishi_144_rejects_settings_outside_the_encoder(self):
        settings = {"power": True, "mode": "heat", "temperature": 22}
        for invalid in ({"temperature": 32}, {"fan": "turbo"}, {"vane": "horizontal"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                mitsubishi.mitsubishi_144_signal(**{**settings, **invalid})

    def test_setup_notice_for_supported_and_unavailable_hubs(self):
        for code, hub_type, manufacturer in (
            (10502, 67, "Daikin"),
            (7404, 30, "BAXI"),
        ):
            with self.subTest(code=code):
                hub, remote = devices(
                    {**AC_ROW, "irDeviceId": code},
                    {**HUB_ROW, "deviceType": hub_type},
                )
                remote, hub = replace(remote, online=True), replace(hub, online=True)
                self.assertIn(manufacturer, backend.ac_setup_notice(remote, (remote, hub)))
                self.assertIn("hub currently unavailable", backend.ac_setup_notice(remote, (remote,)))
                self.assertEqual(backend.ac_setup_notice(hub, (hub,)), "")

    def test_unknown_profile_github_draft_uses_only_catalog_fields(self):
        hub, remote = devices({**AC_ROW, "irDeviceId": 9999}, HUB_ROW)
        remote = replace(remote, name="private-name", room="private-room")
        self.assertNotIn("github.com", backend.ac_setup_notice(remote, (remote, hub)))
        with patch.object(backend, "PROFILE_REPORT_REPOSITORY", "example/orvibo"):
            notice = backend.ac_setup_notice(remote, (remote, hub))
        for manufacturer, reference in (
            ("Mitsubishi Electric", "RH151"),
            ("Mitsubishi Heavy Industries", "RKX502A001C"),
            ("Panasonic", "A75C4762"),
            ("Hitachi", "RAR-2P2"),
            ("Samsung", "DB93-14195A"),
        ):
            with self.subTest(manufacturer=manufacturer):
                self.assertIn(manufacturer, notice)
                self.assertIn(reference, notice)
        self.assertIn("MITSUBISHI_HEAVY_88", notice)
        self.assertIn("MITSUBISHI_HEAVY_152", notice)
        self.assertIn("`Variant to confirm` · AC: CS-E7PKR", notice)
        draft = notice.split("](", 1)[1].split(")", 1)[0]
        url = urlsplit(draft)
        self.assertEqual(url.path, "/example/orvibo/issues/new")
        self.assertEqual(parse_qs(url.query)["body"], [
            "IR catalog profile: 9999\nORVIBO device type/subtype: 5/2\n"
            "Detected hub type: 67\n\nAC brand and model:\nRemote reference:\n"
            "ORVIBO hub model:\nControls tested in HomeMate:\n"
        ])
        for private in ("private-name", "private-room", "virtual-ac", "hardware", "hub-model"):
            self.assertNotIn(private, notice)
        missing = replace(remote, ir_profile_id="injected-private-value")
        self.assertIn("IR catalog profile: not reported", backend.ac_setup_notice(missing, ()))

    def test_exact_match_and_invalid_profile_values(self):
        for value in (None, True, 10502.0, "10502x", "１０５０２", "0", 9999):
            with self.subTest(value=value):
                device, = devices({**AC_ROW, "irDeviceId": value})
                self.assertIsNone(profiles.ac_profile(device))
        for changes in (
            {"subDeviceType": 9},
            {"deviceType": 6},
            {"irDeviceID": 7404},
        ):
            with self.subTest(changes=changes):
                device, = devices({**AC_ROW, **changes})
                self.assertIsNone(profiles.ac_profile(device))
        row = {**AC_ROW, "irDeviceID": "10502"}
        row.pop("irDeviceId")
        device, = devices(row)
        self.assertEqual(profiles.ac_profile(device).manufacturer, "Daikin")

    def test_hub_diagnostics_distinguish_two_cubes_of_the_same_model(self):
        remote, matched, other = devices(
            {**AC_ROW, "deviceId": "ac", "irDeviceId": 7404, "parentUid": "cube-a"},
            {**HUB_ROW, "deviceId": "cube-a", "deviceType": 30},
            {**HUB_ROW, "deviceId": "cube-b", "deviceType": 30, "uid": "other"},
        )
        self.assertEqual(protocol.ac_hub_matches(remote, (matched, other)), [
            {
                "device_type": "30", "same_model": True, "same_cloud_uid": True,
                "parent_match": True, "online": None,
            },
            {
                "device_type": "30", "same_model": True, "same_cloud_uid": False,
                "parent_match": False, "online": None,
            },
        ])

    def test_baxi_candidate_reproduces_the_confirmed_baseline(self):
        device, = devices({**AC_ROW, "irDeviceId": 7404})
        profile = profiles.ac_profile(device)
        baseline = profile.command(profiles.ACState(mode="heat"))
        self.assertEqual(profiles.baxi_7404_candidate("heat", 22, "low"), baseline)
        candidate = profiles.baxi_7404_candidate("cool", 24, "low")
        self.assertEqual(candidate.value2, 211124)
        self.assertEqual(candidate.value4 >> 16, 24)
        self.assertNotEqual(candidate.infrared.pulses, baseline.infrared.pulses)
        verified_cool = profile.command(profiles.ACState(mode="cool"))
        self.assertEqual(verified_cool, profiles.baxi_7404_candidate("cool", 19, "low"))
        self.assertEqual(verified_cool.value4 >> 16, 19)
        self.assertNotEqual(verified_cool, candidate)

    def test_verified_off_frame_and_wire_format(self):
        device, = devices(AC_ROW)
        profile = profiles.ac_profile(device)
        signal = profile.command(profiles.ACState(mode="off")).infrared
        payload = binary.OrviboBinaryClient("test.invalid", "test", "test", "family")
        packet = payload._control_payload(
            device.uid, device.cloud_uid, "ir control", 0, 0, 0, 0, infrared=signal
        )
        self.assertEqual(packet["freq"], 38000)
        self.assertEqual(packet["pluseNum"], 584)
        self.assertEqual(
            hashlib.sha256(packet["pluseData"].encode()).hexdigest(),
            "584c9f76d0aea0da52e97435daaa1cacc41642f26fdf5b04b3fd8d4e1a7e6b0e",
        )
        self.assertEqual(packet["deviceId"], "virtual-ac")
        self.assertEqual(packet["uid"], "hardware")
        for state in (
            profiles.ACState(mode="invalid"),
            profiles.ACState(mode="off", temperature=31),
            profiles.ACState(mode="off", fan="turbo"),
        ):
            with self.subTest(state=state), self.assertRaises(ValueError):
                profile.command(state)


class ClimateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hub, self.child = devices(AC_ROW, HUB_ROW)
        self.send = AsyncMock()
        self.entry = SimpleNamespace(
            entry_id="entry",
            data={"host": "test.invalid", "family_id": "family"},
            options={"selected_device_ids": ["virtual-ac"]},
        )
        self.coordinator = SimpleNamespace(
            entry=self.entry,
            data=SimpleNamespace(
                devices=(self.child, self.hub),
                binary_user_name="test-user",
                binary_password="test-password",
            ),
            last_update_success=True,
            hass=SimpleNamespace(async_add_executor_job=self.send),
            tv_control_lock=asyncio.Lock(),
        )
        self.hass = SimpleNamespace(data={"orvibo_climate_experimental": {"entry": self.coordinator}})
        entities = []
        await climate.async_setup_entry(self.hass, self.entry, entities.extend)
        self.entity, = entities

    async def test_setup_and_explicit_off(self):
        self.send.assert_not_awaited()
        self.assertIsNone(self.entity.hvac_mode)
        self.assertTrue(self.entity.available)
        self.assertTrue(self.entity._attr_supported_features & Features.TURN_OFF)
        await self.entity.async_turn_off()
        self.send.assert_awaited_once()
        args = self.send.await_args.args
        self.assertEqual(args[5:8], ("virtual-ac", "hardware", "ir control"))
        self.assertEqual(len(args[-1].pulses), 584)
        self.assertEqual(self.entity.hvac_mode, HVACMode.OFF)
        self.entity.async_write_ha_state.assert_called_once()

    async def test_baxi_off_uses_virtual_remote_and_scene_signal(self):
        child = replace(self.child, ir_profile_id="7404", online=True)
        hub = replace(self.hub, device_type="30", online=True)
        self.coordinator.data.devices = (child, hub, replace(hub, uid="second-row"))
        entities = []
        await climate.async_setup_entry(self.hass, self.entry, entities.extend)
        entity, = entities
        self.assertTrue(entity.available)
        await entity.async_turn_off()
        self.send.assert_awaited_once()
        args = self.send.await_args.args
        self.assertEqual(args[5:8], ("virtual-ac", "hardware", "ir control"))
        self.assertEqual(args[8:12], (3, 141122, 257, 1476608))
        self.assertEqual(args[-1].frequency, 38000)
        self.assertEqual(len(args[-1].pulses), 212)
        self.assertEqual(
            hashlib.sha256(",".join(map(str, args[-1].pulses)).encode()).hexdigest(),
            "c3c544748ab3f2c89180f701299d920e51c61cc216c380c77e162f1499f87eae",
        )
        self.assertEqual(entity.hvac_mode, HVACMode.OFF)
        self.coordinator.data.devices = (child, replace(hub, cloud_uid="unrelated"))
        self.assertFalse(entity.available)

    async def test_baxi_on_and_follow_up_settings_preserve_requested_state(self):
        child = replace(self.child, ir_profile_id="7404", online=True)
        hub = replace(self.hub, device_type="30", online=True)
        self.coordinator.data.devices = (child, hub)
        entities = []
        await climate.async_setup_entry(self.hass, self.entry, entities.extend)
        entity, = entities
        self.assertEqual(
            entity._attr_supported_features,
            Features.TURN_ON | Features.TURN_OFF | Features.TARGET_TEMPERATURE
            | Features.FAN_MODE | Features.SWING_MODE | Features.PRESET_MODE,
        )
        await entity.async_turn_on()
        self.assertEqual(entity.hvac_mode, HVACMode.HEAT)
        args = self.send.await_args.args
        self.assertEqual(args[8:12], (2, 241122, 257, 1476608))
        self.assertEqual(args[-1].frequency, 38000)
        self.assertEqual(len(args[-1].pulses), 212)
        self.assertEqual(
            hashlib.sha256(",".join(map(str, args[-1].pulses)).encode()).hexdigest(),
            "894d13318cf71f98e29ee97d6d7c0a64d8d41fe8406a3a774d5aa5e6036d6cd4",
        )
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_temperature(temperature=23)
        await entity.async_set_fan_mode("medium")
        await entity.async_set_swing_mode("both")
        args = self.send.await_args.args
        expected = profiles.baxi_7404_candidate(
            "cool", 23, "medium", vertical_swing=True, horizontal_swing=True
        )
        self.assertEqual(args[-1], expected.infrared)
        self.assertEqual(entity.target_temperature, 23)
        self.assertEqual(entity.fan_mode, "medium")
        self.assertEqual(entity.swing_mode, "both")
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_temperature(temperature=24)
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_fan_mode("auto")
        await entity.async_set_swing_mode("horizontal")
        horizontal = profiles.baxi_7404_candidate("cool", 23, "medium", horizontal_swing=True)
        self.assertEqual(self.send.await_args.args[-1], horizontal.infrared)
        self.assertEqual(entity.swing_mode, "horizontal")
        self.assertEqual(self.send.await_count, 6)
        await entity.async_turn_off()
        self.assertEqual(entity.hvac_mode, HVACMode.OFF)
        self.assertEqual(self.send.await_args.args[8:12], (3, 141122, 257, 1476608))

    async def test_baxi_experimental_presets_and_momentary_display(self):
        child = replace(self.child, ir_profile_id="7404", online=True)
        hub = replace(self.hub, device_type="30", online=True)
        self.coordinator.data.devices = (child, hub)
        entities = []
        await climate.async_setup_entry(self.hass, self.entry, entities.extend)
        entity, = entities
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_preset_mode("turbo")
        turbo = profiles.baxi_7404_candidate("cool", 19, "low", trial_extra="turbo")
        self.assertEqual(self.send.await_args.args[-1], turbo.infrared)
        self.assertEqual(entity.preset_mode, "turbo")
        await entity.async_set_preset_mode("display")
        display = profiles.baxi_7404_candidate("cool", 19, "low", trial_extra="display")
        self.assertEqual(self.send.await_args.args[-1], display.infrared)
        self.assertEqual(entity.preset_mode, "none")
        await entity.async_set_temperature(temperature=23)
        baseline = profiles.baxi_7404_candidate("cool", 23, "low")
        self.assertEqual(self.send.await_args.args[-1], baseline.infrared)
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_preset_mode("eco")
        self.assertEqual(self.send.await_count, 4)

    async def test_unselected_and_unknown_remotes_are_skipped(self):
        for options, discovered in (
            ({"selected_device_ids": ["hub"]}, (self.child, self.hub)),
            (self.entry.options, devices({**AC_ROW, "irDeviceId": 9999}, HUB_ROW)),
        ):
            self.entry.options = options
            self.coordinator.data.devices = discovered
            entities = []
            await climate.async_setup_entry(self.hass, self.entry, entities.extend)
            self.assertEqual(entities, [])

    async def test_invalid_controls_never_send(self):
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_set_hvac_mode("invalid")
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_set_temperature(temperature=31)
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_set_fan_mode("turbo")
        self.send.assert_not_awaited()

    async def test_daikin_preserves_v06_settings_and_off_frame(self):
        await self.entity.async_set_temperature(temperature=21)
        await self.entity.async_set_fan_mode("medium")
        self.assertEqual(self.entity._attr_swing_modes, ["off", "vertical"])
        for mode in ("horizontal", "both"):
            with self.assertRaises(HomeAssistantError):
                await self.entity.async_set_swing_mode(mode)
        await self.entity.async_set_swing_mode("vertical")
        await self.entity.async_set_preset_mode("eco_comfort")
        self.send.assert_not_awaited()
        await self.entity.async_set_hvac_mode(HVACMode.COOL)
        for powered in (True, False, True):
            if not powered:
                await self.entity.async_turn_off()
            elif self.entity.hvac_mode == HVACMode.OFF:
                await self.entity.async_turn_on()
            expected = profiles.daikin_signal(
                power=powered, mode="cool", temperature=21, fan="medium",
                eco=True, comfort=True, swing_v=True, swing_h=False,
            )
            self.assertEqual(self.send.await_args.args[-1].pulses, expected.pulses)
        self.assertEqual(self.entity.hvac_mode, HVACMode.COOL)
        self.assertEqual(self.send.await_count, 3)

    async def test_revalidates_device_and_hub_before_sending(self):
        for discovered in (
            (self.child,),
            (self.child, replace(self.hub, online=False)),
            (self.child, replace(self.hub, model="different")),
            (self.child, self.hub, replace(self.hub, uid="other-hub")),
            (replace(self.child, ir_profile_id="7404"), self.hub),
        ):
            self.coordinator.data.devices = discovered
            with self.subTest(discovered=discovered):
                self.assertFalse(self.entity.available)
                with self.assertRaises(HomeAssistantError):
                    await self.entity.async_turn_off()
        self.send.assert_not_awaited()

    async def test_failed_acknowledgement_preserves_unknown_state(self):
        self.send.side_effect = binary.OrviboBinaryError("private data")
        with self.assertRaisesRegex(HomeAssistantError, "did not acknowledge"):
            await self.entity.async_turn_off()
        self.send.assert_awaited_once()
        self.assertIsNone(self.entity.hvac_mode)
        self.entity.async_write_ha_state.assert_not_called()
