"""Documented IR references awaiting an ORVIBO encoder and hardware tests."""

from dataclasses import dataclass
from itertools import groupby


@dataclass(frozen=True, slots=True)
class ACCandidate:
    manufacturer: str
    protocol: str | None
    models: tuple[str, ...] = ()
    remotes: tuple[str, ...] = ()


# Source: https://github.com/crankyoldgit/IRremoteESP8266/blob/master/SupportedProtocols.md
# Models and remotes are independent references within each protocol.
# None records an explicit gap or ambiguity in the source.
AC_CANDIDATES = (
    ACCandidate(
        "Mitsubishi Electric", "MITSUBISHI_AC",
        ("MLZ-RX5017AS", "MSZ-FH…VE", "MSZ-GV2519", "MSZ-SF25VE3", "MSZ-ZW4017S"),
        ("RH151", "RH151/M21ED6426", "SG153/M21EDF426", "SG15D"),
    ),
    ACCandidate("Mitsubishi Electric", "MITSUBISHI112", ("MSH-A24WV", "MUH-A24WV"), ("KPOA",)),
    ACCandidate(
        "Mitsubishi Electric", "MITSUBISHI136",
        ("PEAD-RP71JAA",), ("001CP T7WE10714", "PAR-FA32MA"),
    ),
    ACCandidate("Mitsubishi Electric", None, ("MS-GK24VA",)),
    ACCandidate(
        "Mitsubishi Heavy Industries", "MITSUBISHI_HEAVY_88",
        ("SRK…ZJ-S",), ("RKX502A001C",),
    ),
    ACCandidate(
        "Mitsubishi Heavy Industries", "MITSUBISHI_HEAVY_152",
        ("SRK…ZM-S", "SRK…ZMXA-S"), ("RLA502A700B",),
    ),
    ACCandidate("Panasonic", "PANASONIC_AC32", ("CS-E9CKP series",), ("A75C2295",)),
    ACCandidate(
        "Panasonic", "PANASONIC_AC CKP",
        ("CKP series", "CS-ME10CKPG", "CS-ME12CKPG", "CS-ME14CKPG"), ("A75C2311",),
    ),
    ACCandidate(
        "Panasonic", "PANASONIC_AC DKE",
        ("CS-E12QKEW", "DKE series", "DKW series", "PKR series"),
        ("A75C2616-1", "A75C3704", "PN1122V"),
    ),
    ACCandidate("Panasonic", "PANASONIC_AC JKE", ("CS-YW9MKD", "JKE series"), ("A75C3747",)),
    ACCandidate("Panasonic", "PANASONIC_AC NKE", ("NKE series",)),
    ACCandidate(
        "Panasonic", "PANASONIC_AC RKR",
        ("CS-Z24RKR", "CS-Z9RKR", "RKR series"), ("A75C4762",),
    ),
    # The catalogue labels CS-E7PKR as DKE/2, but the upstream enum assigns
    # variant 2 to NKE and 3 to DKE. Preserve the model without assigning it.
    ACCandidate("Panasonic", None, ("CS-E7PKR",)),
    ACCandidate(
        "Hitachi", "HITACHI_AC1", ("KAZE-312KSDP", "Series VI (circa 2007)"),
        ("LT0541-HTA", "R-LT0541-HTA/Y.K.1.1-1 V2.3"),
    ),
    ACCandidate("Hitachi", "HITACHI_AC3", remotes=("PC-LH3B",)),
    ACCandidate("Hitachi", "HITACHI_AC264", ("RAK-25NH5",), ("RAR-2P2",)),
    ACCandidate("Hitachi", "HITACHI_AC296", ("RAS-70YHA3",), ("RAR-3U3",)),
    ACCandidate("Hitachi", "HITACHI_AC344", ("RAS-22NK",), ("RF11T1",)),
    ACCandidate("Hitachi", "HITACHI_AC424", ("RAS-AJ25H",), ("RAR-8P2",)),
    ACCandidate("Hitachi", None, remotes=("RAS-35THA6",)),
    ACCandidate(
        "Samsung", "SAMSUNG_AC",
        ("AR09FSSDAWKNFA", "AR09HSFSBWKN", "AR12HSSDBWKNEU", "AR12KSFPEWQNET",
         "AR12NXCXAWKXEU", "AR12TXEAAWKNEU"),
        ("DB93-14195A", "DB96-24901C"),
    ),
    ACCandidate("Samsung", None, remotes=("DB63-03556X003", "DB93-16761C", "IEC-R03")),
)


def candidate_references() -> str:
    """Render model and remote references grouped by manufacturer and protocol."""
    sections = []
    for manufacturer, candidates in groupby(AC_CANDIDATES, key=lambda item: item.manufacturer):
        lines = [f"**{manufacturer}**", ""]
        for candidate in candidates:
            details = []
            if candidate.models:
                details.append("AC: " + ", ".join(candidate.models))
            if candidate.remotes:
                details.append("Remotes: " + ", ".join(candidate.remotes))
            protocol = candidate.protocol or "Variant to confirm"
            lines.append(f"- `{protocol}` · " + " · ".join(details))
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
