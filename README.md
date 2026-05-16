# Stash Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ondine/ha-stash?style=for-the-badge)](https://github.com/ondine/ha-stash/releases)
[![License](https://img.shields.io/github/license/ondine/ha-stash?style=for-the-badge)](LICENSE)

Connects [Home Assistant](https://www.home-assistant.io/) to your [Stash](https://github.com/stashapp/stash) media library via its GraphQL API. Provides real-time library statistics, job monitoring, a full library browser, and dashboard controls.

---

## Features

- **Library statistics** — scene, performer, studio, group, tag, gallery and image counts; total size and duration
- **Activity tracking** — O count, play count, scenes played, total play duration
- **Real-time job monitoring** — active job sensor and binary sensor via WebSocket subscription
- **Library browser** — browse scenes, performers, studios and tags directly from the HA media browser UI
- **Dashboard buttons** — one-tap scan, generate, auto-tag, clean, identify, backup, optimise and stop-all-jobs
- **HA services** — trigger any Stash task from automations
- **Version tracking** — current version and update-available binary sensor
- **DLNA status** — binary sensor showing whether DLNA is running
- **Configurable polling** — separate fast (status) and slow (stats) update intervals

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add `https://github.com/ondine/ha-stash` as an **Integration**
4. Search for **Stash** and click **Download**
5. Restart Home Assistant

### Manual

1. Copy `custom_components/stash` into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Stash**
3. Enter your Stash server URL (e.g. `http://192.168.1.179:9999`)
4. Enter your API key — found in Stash under **Settings → Security → Authentication**

### Update Intervals

After setup, click **Configure** on the integration card to adjust polling intervals:

| Setting | Default | Range | Controls |
|---|---|---|---|
| Stats update interval | 300 s (5 min) | 60 – 3600 s | Library counts, sizes, durations, scene history, performers |
| Status update interval | 30 s | 10 – 300 s | Job queue, DLNA status |

Changing either value reloads the integration automatically.

---

## Entities

### Sensors

| Entity | Description | Update |
|---|---|---|
| Scenes | Total scene count | Slow |
| Performers | Total performer count | Slow |
| Studios | Total studio count | Slow |
| Groups | Total group count | Slow |
| Tags | Total tag count | Slow |
| Galleries | Total gallery count | Slow |
| Images | Total image count | Slow |
| O Count | Total O count across all scenes | Slow |
| Total Play Count | Total number of plays across all scenes | Slow |
| Scenes Played | Number of distinct scenes played | Slow |
| Scenes Size | Total size of scene files (GB) | Slow |
| Images Size | Total size of image files (GB) | Slow |
| Scenes Duration | Total scene duration (hours) | Slow |
| Total Play Duration | Total watched time (hours) | Slow |
| Last O Scene | Title of the scene with the highest O count | Slow |
| Last Watched Scene | Title of the most-played scene | Slow |
| Top Performer | Name of the performer with the highest O count | Slow |
| Version | Current Stash server version | Slow |
| Active Job | Description of the currently running job, or "Idle" | Fast |

### Binary Sensors (Diagnostic)

| Entity | Description | Update |
|---|---|---|
| Online | Whether Stash is reachable | Fast |
| Job Running | Whether a job is currently running | Fast |
| DLNA | Whether DLNA is currently active | Fast |
| Update Available | Whether a newer Stash version is available | Slow |
| WebSocket Connected | Whether the real-time WebSocket is connected | Push |

### Buttons

| Button | Action |
|---|---|
| Scan Library | Scan for new or changed files |
| Generate Metadata | Generate thumbnails and previews |
| Auto Tag | Auto-tag scenes by filename |
| Clean Library | Remove missing files from the database |
| Identify Scenes | Auto-identify scenes via scrapers |
| Backup Database | Create a server-side database backup |
| Optimise Database | Run a database optimisation pass |
| Stop All Jobs | Cancel all queued and running jobs |

### Media Player — Library Browser

The **Stash Library** media player entity exposes your full library in the HA media browser. Add a **Media Control** card to your dashboard and click **Browse** to explore:

```
Stash Library
├── Scenes          48 most recent, sorted by date, with thumbnails
├── Performers      Alphabetical, with portrait thumbnails and scene counts
│   └── [Name]     That performer's scenes
├── Studios         Alphabetical, with logo thumbnails and scene counts
│   └── [Name]     That studio's scenes
└── Tags            Tags with at least one scene, alphabetical
    └── [Name]      Scenes with that tag
```

---

## Services

All services can be called from automations, scripts or **Developer Tools → Services**.

| Service | Description |
|---|---|
| `stash.scan` | Scan library for new files |
| `stash.generate` | Generate thumbnails and previews |
| `stash.autotag` | Auto-tag scenes by filename |
| `stash.clean` | Remove missing files from the database |
| `stash.identify` | Auto-identify scenes |
| `stash.backup` | Backup the database |
| `stash.optimise` | Optimise the database |
| `stash.stop_all_jobs` | Cancel all running and queued jobs |

---

## Real-Time Updates via WebSocket

The integration maintains a persistent WebSocket connection to Stash's GraphQL subscription endpoint (`/graphql` over `ws://`). When a job starts, updates or finishes, the status coordinator refreshes immediately rather than waiting for the next poll.

The **WebSocket Connected** binary sensor shows the connection state. If disconnected, the integration reconnects automatically using exponential back-off (5 s → 10 s → 30 s → 60 s → 120 s → 5 min).

The WebSocket uses the `graphql-transport-ws` protocol. If your Stash version uses the older `graphql-ws` protocol, the WebSocket sensor will show disconnected but all polling will continue to work normally.

---

## Troubleshooting

### Cannot Connect

- Check the URL includes `http://` or `https://` and the correct port (default `9999`)
- Verify Stash is running and reachable from the HA host

### Invalid Authentication

- Regenerate the API key in Stash under **Settings → Security → Authentication**
- Ensure the key is pasted without surrounding quotes or spaces

### Sensors showing Unavailable

- Check **Settings → System → Logs** and filter for `stash` — GraphQL errors will identify the exact field causing the failure
- Verify your Stash version supports the queried fields via the Stash GraphQL playground

### WebSocket not connecting

- The integration falls back to polling automatically — all sensors will still update
- Check the HA log for `Stash WebSocket disconnected` messages

### Last Watched Scene / Last O Scene shows wrong value or nothing

- Stash only tracks play counts and O counts when you interact through its own web UI
- External players do not update these counters unless integrated separately

---

## Links

- [Stash](https://github.com/stashapp/stash)
- [Stash API documentation](https://docs.stashapp.cc)
- [Issues](https://github.com/ondine/ha-stash/issues)
- [Home Assistant](https://www.home-assistant.io/)

## License

MIT — see [LICENSE](LICENSE)
