# Changelog

## 1.1.1

- Streamlined every spoken announcement: shorter wording, "left" instead of "remaining", dropped the redundant "Pomodoro" prefix.
- Fixed singular/plural in time and session-count announcements ("1 minute" no longer reads as "1 minutes").

## 1.1.0

- Added a new option to play a short attention-ping tone alongside the periodic time-remaining announcement.
- Tick tone is gated independently of the phase-transition tones, so the two can be toggled separately.

## 1.0.1

- Shortened all phase-transition tones (30-45% shorter) for a less intrusive feel.
- Reworked tone patterns to use only C major scale notes for musical consistency.
- Added pause and resume tones (previously silent).
- Refactored tone playback to a data-driven lookup table for easier future tuning.

## 1.0.0

- Initial release.
- Configurable work / short break / long break durations and long-break interval.
- Five gestures: start/pause, stop, status, skip phase, reset session counter.
- Phase-transition tones and speech announcements.
- Optional periodic time-remaining announcement.
- Settings panel under NVDA Preferences.
