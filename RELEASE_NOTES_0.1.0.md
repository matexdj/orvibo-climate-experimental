# ORVIBO Climate Experimental v0.1.0

The published source preview requires separately provisioned ORVIBO TLS client material for live operation.

Control selected split air conditioners in Home Assistant using the ORVIBO hub and virtual remote you already set up in HomeMate. Commands travel through ORVIBO Cloud.

| Verified setup | HomeMate IR profile | Controls |
| --- | --- | --- |
| Daikin with an ARC433A87-compatible remote and Allone Pro | `10502` | Power, mode, target temperature, fan speed, vertical swing, Eco and Comfort |
| BAXI Anori JSG35 with Magic Cube | `7404` | Power, heat, cool, target temperature, fan speed, vertical and horizontal swing, Turbo, Silence, Display and iFeel |

Both setups responded in a fresh Home Assistant OS installation. Home Assistant shows the last acknowledged command as assumed state. Changes made with a physical remote may leave that state out of sync. See [installation](INSTALL.md) and [contributing a profile](CONTRIBUTING.md) for the setup steps and the details you can safely share.

The verified profiles are enabled automatically when the virtual remote and hub match. Candidate protocols for additional brands need an exact HomeMate profile match and a hardware test before they can control an air conditioner.

Based on ORVIBO Cloud 1.3.2 by Kosztyk, which derives from maycode0-0's integration. See [LICENSE](LICENSE).
