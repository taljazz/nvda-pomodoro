# Pomodoro Timer add-on for NVDA
# A focused-work timer that announces work/break transitions through speech and tones.

from typing import Callable, Optional

import wx

import config
import globalPluginHandler
import gui
import scriptHandler
import tones
import ui
from logHandler import log

import addonHandler

from .pomodoroSettings import PomodoroSettingsPanel, CONFIG_SECTION
from .pomodoroTimer import (
	PHASE_IDLE,
	PHASE_LONG_BREAK,
	PHASE_SHORT_BREAK,
	PHASE_WORK,
	PomodoroTimer,
)

addonHandler.initTranslation()
_: Callable[[str], str]


# Persisted configuration. Defaults match the classic pomodoro technique:
# 25 minute work, 5 minute short break, 15 minute long break, long break every 4 sessions.
confspec = {
	"workMinutes": "integer(default=25, min=1, max=180)",
	"shortBreakMinutes": "integer(default=5, min=1, max=60)",
	"longBreakMinutes": "integer(default=15, min=1, max=120)",
	"sessionsBeforeLongBreak": "integer(default=4, min=1, max=20)",
	"autoStartBreaks": "boolean(default=True)",
	"autoStartWork": "boolean(default=False)",
	"playTransitionTone": "boolean(default=True)",
	"speakOnTransition": "boolean(default=True)",
	"tickIntervalMinutes": "integer(default=0, min=0, max=30)",
	"playTickTone": "boolean(default=True)",
}
config.conf.spec[CONFIG_SECTION] = confspec


# Tone patterns. Each entry is a list of (frequencyHz, durationMs) tuples played in order.
# All notes are drawn from the C major scale so any pattern composes pleasantly with any other.
# Total length per pattern is kept under ~400ms so a tone never crowds the speech that follows.
TONE_PATTERNS = {
	# Three-note ascending arpeggio (C5 E5 G5): "begin focus".
	"work": [(523, 70), (659, 70), (784, 130)],
	# Falling perfect fifth (G5 -> C5): "settle, ease back".
	"shortBreak": [(784, 80), (523, 130)],
	# Four-note ascending arpeggio reaching the octave (C5 E5 G5 C6): "well earned".
	"longBreak": [(523, 70), (659, 70), (784, 70), (1047, 160)],
	# Falling perfect fifth in the low register (G4 -> C4): "stopped, closed".
	"idle": [(392, 70), (262, 110)],
	# Two quick ascending pings in the upper register (E5 A5): "your attention".
	"ready": [(659, 60), (880, 90)],
	# Two short tones, descending step (E5 C5): "held in place".
	"paused": [(659, 50), (523, 70)],
	# Two short tones, ascending step (C5 E5) — mirror of paused: "moving again".
	"resumed": [(523, 50), (659, 70)],
	# A single soft high ping (A5) — precedes the periodic time-remaining announcement.
	# Kept deliberately tiny so it cues the ear without intruding on deep focus.
	"tick": [(880, 50)],
}


def _formatRemaining(seconds: float) -> str:
	"""Format remaining time as 'X minutes Y seconds', minutes-only, or seconds-only.

	Handles singular/plural so "1 minute" never reads as "1 minutes".
	"""
	seconds = max(0, int(round(seconds)))
	minutes, sec = divmod(seconds, 60)
	parts = []
	if minutes == 1:
		# Translators: singular minute in a duration string.
		parts.append(_("1 minute"))
	elif minutes > 0:
		# Translators: plural minutes in a duration string.
		parts.append(_("{n} minutes").format(n=minutes))
	if sec == 1:
		# Translators: singular second in a duration string.
		parts.append(_("1 second"))
	elif sec > 0:
		# Translators: plural seconds in a duration string.
		parts.append(_("{n} seconds").format(n=sec))
	if not parts:
		return _("0 seconds")
	return " ".join(parts)


def _formatSessions(n: int) -> str:
	"""Format a session count as '1 session' or 'N sessions'."""
	if n == 1:
		# Translators: singular session in a count.
		return _("1 session")
	# Translators: plural sessions in a count.
	return _("{n} sessions").format(n=n)


def _phaseLabel(phase: str) -> str:
	"""User-visible label for a phase id."""
	if phase == PHASE_WORK:
		return _("Work")
	if phase == PHASE_SHORT_BREAK:
		return _("Short break")
	if phase == PHASE_LONG_BREAK:
		return _("Long break")
	return _("Idle")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	# Translators: category for the Pomodoro Timer gestures in Input Gestures.
	scriptCategory = _("Pomodoro Timer")

	def __init__(self) -> None:
		super().__init__()
		self._timer = PomodoroTimer(self._currentDurations, self._onPhaseChange)
		self._tickCallLater: Optional[wx.CallLater] = None
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(PomodoroSettingsPanel)

	def terminate(self) -> None:
		self._cancelTick()
		try:
			self._timer.stop()
		except Exception:
			log.exception("Pomodoro: error stopping timer during terminate")
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(PomodoroSettingsPanel)
		except ValueError:
			pass
		super().terminate()

	# ---- configuration accessor passed to the timer ----------------------------

	def _currentDurations(self) -> dict:
		conf = config.conf[CONFIG_SECTION]
		return {
			"workMinutes": conf["workMinutes"],
			"shortBreakMinutes": conf["shortBreakMinutes"],
			"longBreakMinutes": conf["longBreakMinutes"],
			"sessionsBeforeLongBreak": conf["sessionsBeforeLongBreak"],
			"autoStartBreaks": conf["autoStartBreaks"],
			"autoStartWork": conf["autoStartWork"],
		}

	# ---- phase-change notification ---------------------------------------------

	def _onPhaseChange(self, prevPhase: str, newPhase: str, completedSessions: int) -> None:
		conf = config.conf[CONFIG_SECTION]
		# Phases prefixed with "ready:" mean a phase finished but the next one is parked
		# waiting for the user to start it (because autoStart for that phase is off).
		if newPhase.startswith("ready:"):
			queued = newPhase[len("ready:"):]
			self._playTone("ready")
			if conf["speakOnTransition"]:
				# Translators: spoken when a phase ends and the next one is waiting for the user to start it.
				ui.message(
					_("{phase} done. Press start for {next}.").format(
						phase=_phaseLabel(prevPhase), next=_phaseLabel(queued).lower()
					)
				)
			self._cancelTick()
			return

		# Real phase change.
		if newPhase == PHASE_IDLE:
			# Stopped manually.
			self._cancelTick()
			self._playTone(PHASE_IDLE)
			if conf["speakOnTransition"] and prevPhase != PHASE_IDLE:
				# Translators: spoken when the user stops the timer.
				ui.message(_("Stopped."))
			return

		# Starting or auto-starting a new phase.
		self._playTone(newPhase)
		if conf["speakOnTransition"]:
			duration = _formatRemaining(self._timer.remaining())
			if newPhase == PHASE_WORK:
				# Translators: spoken when a work phase begins. {n} is the upcoming session number.
				msg = _("Work session {n}. {duration}.").format(
					n=completedSessions + 1,
					duration=duration,
				)
			else:
				# Translators: spoken when a break phase begins.
				msg = _("{phase}. {duration}.").format(
					phase=_phaseLabel(newPhase), duration=duration
				)
			ui.message(msg)
		self._scheduleTick()

	# ---- periodic tick announcements -------------------------------------------

	def _scheduleTick(self) -> None:
		self._cancelTick()
		minutes = config.conf[CONFIG_SECTION]["tickIntervalMinutes"]
		if minutes <= 0:
			return
		self._tickCallLater = wx.CallLater(minutes * 60 * 1000, self._onTick)

	def _cancelTick(self) -> None:
		if self._tickCallLater is not None:
			try:
				if self._tickCallLater.IsRunning():
					self._tickCallLater.Stop()
			except Exception:
				pass
			self._tickCallLater = None

	def _onTick(self) -> None:
		if not self._timer.isRunning:
			return
		remaining = self._timer.remaining()
		# Don't announce if the phase is about to end in the next few seconds — the
		# phase-end announcement will cover it.
		if remaining > 5:
			# Soft attention ping first, then the spoken update. The tone is short
			# enough that NVDA starts the speech almost immediately after.
			self._playTone("tick")
			ui.message(
				# Translators: periodic reminder while a phase is running.
				_("{phase}, {remaining} left.").format(
					phase=_phaseLabel(self._timer.phase),
					remaining=_formatRemaining(remaining),
				)
			)
		self._scheduleTick()

	# ---- tones -----------------------------------------------------------------

	def _playTone(self, key: str) -> None:
		"""Play the named tone pattern from TONE_PATTERNS, if its config gate is on.

		`key` is one of the TONE_PATTERNS keys (e.g. "work", "shortBreak", "paused", "tick").
		The phase constants happen to match the work/shortBreak/longBreak/idle keys,
		so callers can pass a phase string directly. The "tick" tone is gated by its own
		setting (playTickTone) since users may want focus pings without the louder phase
		transition tones, or vice versa.
		"""
		gateKey = "playTickTone" if key == "tick" else "playTransitionTone"
		if not config.conf[CONFIG_SECTION][gateKey]:
			return
		pattern = TONE_PATTERNS.get(key)
		if not pattern:
			return
		try:
			for hz, ms in pattern:
				tones.beep(hz, ms)
		except Exception:
			log.exception("Pomodoro: tone playback failed")

	# ---- scripts (gestures) ----------------------------------------------------

	@scriptHandler.script(
		# Translators: described in Input help for the start/pause Pomodoro gesture.
		description=_("Pomodoro: start a new session, or pause or resume the current one."),
		gesture="kb:NVDA+alt+p",
	)
	def script_startPause(self, gesture) -> None:
		action = self._timer.startOrResume()
		if action == "paused":
			self._playTone("paused")
			ui.message(
				# Translators: spoken when the user pauses the timer.
				_("Paused in {phase}. {remaining} left.").format(
					phase=_phaseLabel(self._timer.phase).lower(),
					remaining=_formatRemaining(self._timer.remaining()),
				)
			)
			self._cancelTick()
		elif action == "resumed":
			self._playTone("resumed")
			ui.message(
				# Translators: spoken when the user resumes a paused timer.
				_("Resumed. {remaining} left.").format(
					remaining=_formatRemaining(self._timer.remaining())
				)
			)
			self._scheduleTick()
		# 'started' is announced by the phase-change handler.

	@scriptHandler.script(
		# Translators: described in Input help for the stop Pomodoro gesture.
		description=_("Pomodoro: stop the timer and reset the session counter."),
		gesture="kb:NVDA+alt+s",
	)
	def script_stop(self, gesture) -> None:
		if self._timer.phase == PHASE_IDLE and not self._timer.isPaused:
			# Translators: spoken when the user invokes stop while no timer is running.
			ui.message(_("Not running."))
			return
		self._timer.stop()

	@scriptHandler.script(
		# Translators: described in Input help for the status Pomodoro gesture.
		description=_("Pomodoro: speak the current phase, time remaining, and completed sessions."),
		gesture="kb:NVDA+alt+t",
	)
	def script_status(self, gesture) -> None:
		sessions = _formatSessions(self._timer.completedWorkSessions)
		if self._timer.phase == PHASE_IDLE and not self._timer.isPaused:
			ui.message(
				# Translators: status spoken when no Pomodoro is running.
				_("Idle. {sessions} done.").format(sessions=sessions)
			)
			return
		state = _("paused") if self._timer.isPaused else _("running")
		ui.message(
			# Translators: status spoken when a Pomodoro is running or paused.
			_("{phase}, {state}. {remaining} left. {sessions} done.").format(
				phase=_phaseLabel(self._timer.phase),
				state=state,
				remaining=_formatRemaining(self._timer.remaining()),
				sessions=sessions,
			)
		)

	@scriptHandler.script(
		# Translators: described in Input help for the skip-phase Pomodoro gesture.
		description=_("Pomodoro: skip the current phase and advance to the next one."),
		gesture="kb:NVDA+alt+k",
	)
	def script_skip(self, gesture) -> None:
		if self._timer.phase == PHASE_IDLE:
			ui.message(_("Not running."))
			return
		self._timer.skip()

	@scriptHandler.script(
		# Translators: described in Input help for the reset-session-counter Pomodoro gesture.
		description=_("Pomodoro: reset the completed session counter to zero."),
		gesture="kb:NVDA+alt+r",
	)
	def script_resetSessions(self, gesture) -> None:
		self._timer.resetSessionCount()
		# Translators: spoken when the user resets the completed session counter.
		ui.message(_("Counter reset."))
