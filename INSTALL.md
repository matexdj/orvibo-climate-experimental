# Install ORVIBO Climate Experimental 0.1.0

In HomeMate, add the air conditioner as a virtual remote from inside its ORVIBO hub, then check that the app controls it. The verified setups are a Daikin with an ARC433A87-compatible remote (profile 10502, Allone Pro) and a BAXI Anori JSG35 (profile 7404, Magic Cube). The integration uses ORVIBO Cloud.

## Install from the local review ZIP

1. Extract the ZIP. Copy `custom_components/orvibo_climate_experimental` into your Home Assistant configuration folder. Check that the manifest is at `/config/custom_components/orvibo_climate_experimental/manifest.json`.
2. If updating a previous experimental build, back up and replace that folder. Upstream ORVIBO Cloud uses its own `orvibo_cloud` folder.
3. Restart Home Assistant. Go to **Settings → Devices & services → Add integration** and search for **ORVIBO Climate Experimental**.
4. Choose the server where HomeMate lists your devices and enter your own HomeMate credentials in Home Assistant. Select your home and the AC remotes you want to add. The corresponding hubs must be visible in discovery.
5. Open each climate entity and test power, temperature, fan speed and swing while you can see the unit. Add the entity to a dashboard using a Thermostat or Tile card.

If an AC remote appears without a climate entity, follow the [profile contribution guide](CONTRIBUTING.md). The displayed state represents the last acknowledged request and can differ from the air conditioner's state after using its physical remote.

## Marketplace or HACS

Marketplace installation is pending. The public source omits the shared ORVIBO TLS client key required for live operation. The manual steps above refer to the local review ZIP used for hardware testing. If you already have authorized ORVIBO client material, provide the matching certificate and key locally as `orvibo_client_cert.pem` and `orvibo_client_key.pem` inside the integration folder. Keep the key outside public repositories and diagnostics.

1. Open **Settings → Marketplace → Add from link**. On installations using HACS, open **HACS → Custom repositories**.
2. Enter the published fork URL. Choose **Integration** if prompted.
3. Install **ORVIBO Climate Experimental**, restart Home Assistant and follow steps 3–5 above.

See the [Marketplace documentation](https://www.home-assistant.io/integrations/marketplace/#custom-repositories).

## Uninstall

Remove the entry under **Devices & services**. Uninstall it through Marketplace or HACS if you used either to install it. For a manual installation, remove `custom_components/orvibo_climate_experimental` and restart Home Assistant.
