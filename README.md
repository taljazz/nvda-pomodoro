# Pomodoro Timer for NVDA

A focused-work timer based on the [Pomodoro Technique](https://en.wikipedia.org/wiki/Pomodoro_Technique), built specifically for NVDA screen reader users. Phase transitions are announced through brief speech and short musical tones so you can stay focused on your work without watching a clock.

## What it does

- **25 minute** focused work sessions followed by a **5 minute** short break.
- After every **4 work sessions**, a **15 minute** long break instead of a short break.
- All durations and behaviours are configurable from NVDA Settings → Pomodoro Timer.

## Default gestures

All gestures are rebindable from NVDA's Input Gestures dialog under the **Pomodoro Timer** category.

| Gesture | Action |
| --- | --- |
| NVDA+Alt+P | Start a new session, or pause / resume the current one. |
| NVDA+Alt+S | Stop the timer and reset the session counter. |
| NVDA+Alt+T | Speak current phase, time remaining, and completed sessions. |
| NVDA+Alt+N | Skip the current phase and advance to the next one. |
| NVDA+Alt+R | Reset the completed session counter without stopping a running phase. |

## Installation

### From a release build

1. Download the latest `pomodoro-X.Y.Z.nvda-addon` file from the [Releases page](https://github.com/taljazz/nvda-pomodoro/releases) (or once approved, from the NVDA Add-on Store).
2. Open the file. NVDA will prompt you to install it.
3. Restart NVDA when prompted.

### From source

1. Clone this repository.
2. Run `powershell -ExecutionPolicy Bypass -File .\build.ps1` (or use the inline build command in `build.ps1` if your execution policy is restricted).
3. The built `pomodoro-X.Y.Z.nvda-addon` appears in `dist/`. Open it as above.

## Project layout

```
pomodoro/
├── manifest.ini                  Add-on metadata read by NVDA
├── globalPlugins/pomodoro/
│   ├── __init__.py               GlobalPlugin: gestures, announcements, tones
│   ├── pomodoroTimer.py          State machine (idle/work/break/long break)
│   └── pomodoroSettings.py       Settings panel registered in NVDA Settings
├── doc/en/readme.html            User-facing help shipped inside the add-on
├── build.ps1                     Rebuilds the .nvda-addon package
├── CHANGELOG.md                  Release notes per version
├── LICENSE                       GPL v2
└── README.md                     You are here
```

## Settings

Open **NVDA menu → Preferences → Settings → Pomodoro Timer**. All options:

- **Work duration**, **short break duration**, **long break duration** — defaults 25 / 5 / 15 minutes.
- **Work sessions before a long break** — default 4.
- **Automatically start breaks when work ends** — on by default.
- **Automatically start the next work session when a break ends** — off by default (so an unattended computer doesn't silently begin a new work phase).
- **Play tones at phase transitions** — on by default.
- **Speak announcements at phase transitions** — on by default.
- **Announce remaining time every N minutes** — periodic reminder; default 0 (off).
- **Play a short tone with the periodic time-remaining announcement** — on by default; gated independently of the phase-transition tones.

## Releasing a new version

1. Bump `version =` in `manifest.ini`.
2. Add a section at the top of `CHANGELOG.md`.
3. Run `build.ps1`. Confirm `dist/pomodoro-X.Y.Z.nvda-addon` is produced.
4. Tag: `git tag vX.Y.Z && git push --tags`.
5. Create a GitHub release attaching `dist/pomodoro-X.Y.Z.nvda-addon`.
6. For the NVDA Add-on Store: open a new issue on [nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml) and fill in the form with the release download URL.

## License

GPL v2 or later. See [LICENSE](LICENSE).

