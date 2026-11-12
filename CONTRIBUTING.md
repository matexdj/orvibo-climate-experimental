# Contribute an IR profile

Add the air conditioner from inside its hub in HomeMate and verify that the app can control it. In Home Assistant, select the virtual remote in ORVIBO Climate Experimental. Its device settings show whether its profile is supported and provide a report you can copy. Once the public repository is configured, the GitHub link opens a draft issue for you to review and submit.

Paste only the following details into the issue:

```text
Air conditioner brand and exact model:
Remote model printed on the remote, without serial number:
ORVIBO hub model:
Home Assistant, HomeMate and integration versions:
HomeMate device_type:
HomeMate sub_device_type:
ir_profile_id (public IR catalog identifier):
Hub type and match flags, if available:
Controls that worked in HomeMate:
Controls that did not respond:
```

If you need to look up these fields, download diagnostics from the integration entry under **Settings → Devices & services**. Open the file locally and copy only the requested fields. Keep full diagnostics, captures, account details, password hashes, tokens, private URLs, IP and MAC addresses, and identifiers for people, homes and devices private.

The setup assistant groups candidate remote references by protocol for Mitsubishi Electric, Mitsubishi Heavy Industries, Panasonic, Hitachi and Samsung. The matching protocol is a starting point. Each candidate needs an exact HomeMate profile and a hardware test. If HomeMate can save an OFF action in a scene, it may store the signal. Share only its frequency and pulse durations, the represented settings, and the source, with permission to distribute the sample.

When adding code, register the exact type, subtype and profile in `ac_profiles.py`, restrict it to the compatible hub, and expose only supported controls. Add tests for profile matching, representative signals and unsupported settings. Run `python -m unittest discover -s tests -v`.
