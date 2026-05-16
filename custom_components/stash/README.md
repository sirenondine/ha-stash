# Stash Home Assistant Integration

This integration connects Home Assistant to your [Stash](https://github.com/stashapp/stash) library via the GraphQL API, providing sensors with library statistics.

## Features

- **Config Flow Setup**: Easy UI-based configuration
- **Library Statistics Sensors**:
  - Scene Count
  - Performer Count
  - Studio Count
  - Movie Count
  - Tag Count
  - Gallery Count
  - Image Count
  - Total Library Size (in GB)
  - Total Library Duration (in hours)

## Installation

### Option 1: Manual Installation

1. Copy the `custom_components/stash` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings** > **Devices & Services** > **Add Integration**.
4. Search for "Stash" and follow the setup wizard.

### Option 2: HACS (Home Assistant Community Store)

1. Add this repository as a custom repository in HACS.
2. Install the integration through HACS.
3. Restart Home Assistant.
4. Go to **Settings** > **Devices & Services** > **Add Integration**.
5. Search for "Stash" and follow the setup wizard.

## Configuration

### Via UI (Recommended)

1. Navigate to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for "Stash".
3. Enter your Stash server URL (e.g., `http://192.168.1.179:9999`).
4. Enter your Stash API Key (found in Stash under **Settings** > **Security** > **Authentication**).

### Finding Your API Key

1. Open Stash in your browser.
2. Go to **Settings** > **Security** > **Authentication**.
3. Copy the API Key.

## Sensors

The integration creates the following sensors:

| Sensor | Description | Unit |
|--------|-------------|------|
| Scenes | Total number of scenes in your library | - |
| Performers | Total number of performers | - |
| Studios | Total number of studios | - |
| Movies | Total number of movies | - |
| Tags | Total number of tags | - |
| Galleries | Total number of galleries | - |
| Images | Total number of images | - |
| Total Size | Total size of all files in your library | GB |
| Total Duration | Total duration of all scenes | Hours |

## Update Interval

The integration polls the Stash API every 5 minutes by default. This can be adjusted in the `const.py` file by modifying the `SCAN_INTERVAL` value (in seconds).

## Troubleshooting

### Cannot Connect

- Verify the Stash server is running and accessible.
- Check that the URL is correct (include `http://` or `https://`).
- Ensure the port is correct (default is 9999).

### Invalid Authentication

- Verify the API key is correct.
- Check that API key authentication is enabled in Stash.

### No Data

- Check the Home Assistant logs for errors.
- Verify the Stash GraphQL API is working by testing it in the Stash GraphQL playground.

## License

MIT License
