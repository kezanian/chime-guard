# Chime Guard: Silent Google Cast Playback for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/kezanian/chime-guard?color=blue)](https://github.com/kezanian/chime-guard/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Chime Guard** eliminates the infamous, unconfigurable connect chime ("beep") that Google Home, Nest Audio, and Chromecast speakers play every time an audio stream begins or transitions.

---

## The Problem
Google Cast devices enforce a firmware-level connect sound whenever:
1. **Cold Start**: Starting playback while the speaker is off, idle, or in standby.
2. **App Handoff**: Switching from an external stream (e.g. Spotify cast from a phone) to Home Assistant or Music Assistant.

Until now, the only workarounds were brittle custom YAML scripts that set volume to 0% and failed whenever someone clicked "Play" in a Lovelace dashboard or used Music Assistant.

## The Solution
Chime Guard acts as an intelligent protective layer across both the **Home Assistant Frontend** and **Backend**:
- **Automatic Frontend Hook**: Transparently intercepts `media_player` and `music_assistant` play calls directly from dashboard cards and UI controls.
- **Chime Absorption**: Rapidly mutes the physical Google Cast speaker, dispatches the stream, enforces an optimal 1.8-second chime absorption window, and polls until media is actively playing before seamlessly unmuting.
- **External Stream Detection**: Detects when mobile Spotify or YouTube is playing and treats app handoffs like cold starts to swallow the handover chime.
- **Instant Track Navigation**: Detects active in-session playback so Next, Previous, and Resume commands remain instantaneous.

---

## Architecture

```
[ Dashboard Cards / Music Assistant / Automations ]
                        │
                        ▼ (media_player.play_media / mass.play_media)
                 [ CHIME GUARD ]
                        │
      ┌─────────────────┴─────────────────┐
      │ 1. volume_mute: true              │ 2. Start Playback
      ▼                                   ▼
[ Physical Google Cast Speaker ]    [ Audio Stream / Music Assistant ]
      │ (Hardware chime swallowed silently)
      ▼
[ Wait 1.8s + Poll 'playing' state ]
      │
      ▼ 3. volume_mute: false
[ Clean, Uninterrupted Audio ]
```

---

## Installation

### Via HACS (Recommended)
1. In Home Assistant, open **HACS** > **Integrations**.
2. Click the three dots in the top right corner > **Custom repositories**.
3. Add repository URL: `https://github.com/kezanian/chime-guard` with category **Integration**.
4. Search for **Chime Guard** and click **Download**.
5. Restart Home Assistant.
6. In Home Assistant, go to **Settings** > **Devices & Services** > **Add Integration**, search for **Chime Guard**, and follow the on-screen prompts.

---

## Configuration & Options
After adding Chime Guard, click **Configure** on the integration card to adjust settings:

| Option | Default | Description |
|---|---|---|
| **Minimum Mute Duration** | `1800 ms` | Duration to hold mute so the connect chime is 100% absorbed before unmuting. |
| **Safety Timeout** | `12 s` | Maximum time before safety unmute in case of network drops or stalled streams. |
| **External Takeover Protection** | `Enabled` | Suppresses chime when taking over active Spotify/YouTube mobile cast streams. |
| **Intercept Speaker Groups** | `Enabled` | Suppresses connect chime when adding speakers to an active group (`media_player.join`). |
| **Mute Method** | `volume_mute` | Standard mute toggle (preserves volume slider) or volume-zero fallback. |

---

## Automations & Scripts Usage
For automations, voice assistants, or NFC tags, Chime Guard provides drop-in services:

```yaml
action: chime_guard.silent_play
target:
  entity_id: media_player.kitchen_speaker
data:
  media_content_id: "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
  media_content_type: "playlist"
```

---

## License
MIT License. Created by [kezanian](https://github.com/kezanian). Community contributions are welcome!
