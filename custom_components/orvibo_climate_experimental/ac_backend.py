"""Route AC infrared commands through the existing ORVIBO TLS client."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlencode

from homeassistant.exceptions import HomeAssistantError

from .ac_candidates import candidate_references
from .ac_profiles import ACProfile, ac_profile
from .binary import OrviboBinaryError, control_device
from .const import CONF_FAMILY_ID, CONF_HOST
from .control import OrviboControlCommand
from .coordinator import OrviboCloudCoordinator
from .protocol import OrviboDevice, ac_hub_matches

# Set to "owner/repository" when the public fork is approved.
PROFILE_REPORT_REPOSITORY: str | None = None


def has_available_route(
    device: OrviboDevice, devices: Iterable[OrviboDevice], hub_type: str
) -> bool:
    """Check the hub association without routing a command to a hub row."""
    if not device.uid or not device.cloud_uid or not device.model:
        return False
    matches = [
        hub for hub in devices
        if hub.device_type == hub_type and hub.cloud_uid == device.cloud_uid
        and hub.model == device.model
    ]
    if hub_type == "30":
        # The Magic Cube can appear as multiple rows sharing the same route.
        return device.online is True and any(hub.online is True for hub in matches)
    return len(matches) == 1 and matches[0].online is not False


def ac_setup_notice(
    device: OrviboDevice, devices: tuple[OrviboDevice, ...]
) -> str:
    """Explain compatibility and provide a report containing only catalog metadata."""
    if (device.device_type, device.sub_device_type) != ("5", "2"):
        return ""
    profile = ac_profile(device)
    if profile is not None:
        if device.online is not False and has_available_route(device, devices, profile.hub_type):
            return f"\n\n**IR profile supported:** {profile.manufacturer} ({device.ir_profile_id})."
        return (
            "\n\n**IR profile supported, hub currently unavailable.** "
            "Check that the AC is configured inside its hub in HomeMate and that both are online."
        )

    raw_code = device.ir_profile_id
    code = raw_code if raw_code.isascii() and raw_code.isdecimal() and len(raw_code) <= 12 else "not reported"
    hub_types = sorted({
        match["device_type"]
        for match in ac_hub_matches(device, devices)
        if match["same_cloud_uid"] or match["parent_match"]
    })
    hubs = ", ".join(hub_types) or "not detected"
    report = f"IR catalog profile: {code}\nORVIBO device type/subtype: 5/2\nDetected hub type: {hubs}"
    notice = (
        "\n\n**IR profile not supported yet.** This selection will not create a thermostat. "
        "First check that the AC responds in HomeMate. To request support, review the report "
        "below and add the exact AC model, remote reference, hub model and controls tested. "
        "Keep credentials, serial numbers and full diagnostics private.\n\n"
        f"```text\n{report}\n```"
    )
    if PROFILE_REPORT_REPOSITORY:
        repo_url = f"https://github.com/{PROFILE_REPORT_REPOSITORY}"
        query = urlencode({
            "title": "New AC IR profile",
            "body": (
                f"{report}\n\nAC brand and model:\nRemote reference:\n"
                "ORVIBO hub model:\nControls tested in HomeMate:\n"
            ),
        })
        notice += (
            f"\n\n[Open a GitHub issue draft]({repo_url}/issues/new?{query}) · "
            f"[Contribution guide]({repo_url}/blob/HEAD/CONTRIBUTING.md). "
            "Review the draft and submit it in GitHub."
        )
    return (
        f"{notice}\n\n**Documented IR references**\n\n"
        "If your AC or remote matches a reference below, include the exact model and remote in the report. "
        "These references are for identification and cannot send commands yet.\n\n"
        f"{candidate_references()}"
    )


class OrviboACBackend:
    """Resolve current routing and send one validated IR signal."""

    def __init__(self, coordinator: OrviboCloudCoordinator, profile: ACProfile) -> None:
        self.coordinator = coordinator
        self.profile = profile

    def available(self, device: OrviboDevice) -> bool:
        account = self.coordinator.data
        return (
            self.coordinator.last_update_success
            and device.online is not False
            and has_available_route(device, account.devices, self.profile.hub_type)
            and bool(account.binary_user_name and account.binary_password)
        )

    async def async_send(
        self, device: OrviboDevice, command: OrviboControlCommand
    ) -> None:
        """Send under the caller's control lock without retrying on failure."""
        if not self.available(device):
            raise HomeAssistantError("The ORVIBO AC remote is unavailable")
        account = self.coordinator.data
        entry_data = self.coordinator.entry.data
        try:
            await self.coordinator.hass.async_add_executor_job(
                control_device,
                entry_data[CONF_HOST],
                account.binary_user_name,
                account.binary_password,
                entry_data[CONF_FAMILY_ID],
                device.uid,
                device.cloud_uid,
                command.order, command.value1, command.value2, command.value3,
                command.value4, command.properties, command.infrared,
            )
        except (OrviboBinaryError, OSError):
            raise HomeAssistantError("ORVIBO did not acknowledge the AC command") from None
