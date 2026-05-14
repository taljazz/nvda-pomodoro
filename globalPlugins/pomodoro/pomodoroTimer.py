# Pomodoro Timer add-on for NVDA
# State machine and scheduling logic.

import time
from typing import Callable, Optional

import wx


# Phase identifiers. Strings make logs and debugging readable.
PHASE_IDLE = "idle"
PHASE_WORK = "work"
PHASE_SHORT_BREAK = "shortBreak"
PHASE_LONG_BREAK = "longBreak"


class PomodoroTimer:
	"""Single-shot pomodoro state machine driven by wx.CallLater.

	A wx.CallLater is used (instead of threading.Timer) so the callback fires on
	the main thread, which is the thread NVDA expects for speech and UI work.

	The caller supplies an `onPhaseChange(prevPhase, newPhase, completedWorkSessions)`
	callback that is invoked whenever the timer transitions between phases (including
	at start and stop). The plugin uses it to announce the new phase and play tones.
	"""

	def __init__(
		self,
		getDurations: Callable[[], dict],
		onPhaseChange: Callable[[str, str, int], None],
	) -> None:
		# `getDurations` is a callable that returns a fresh dict each call so we always
		# pick up the latest user settings without holding a stale reference.
		# Expected keys: workMinutes, shortBreakMinutes, longBreakMinutes,
		# sessionsBeforeLongBreak, autoStartBreaks, autoStartWork.
		self._getDurations = getDurations
		self._onPhaseChange = onPhaseChange

		self._phase: str = PHASE_IDLE
		self._phaseStart: float = 0.0
		self._phaseDuration: float = 0.0
		self._pausedRemaining: Optional[float] = None
		self._completedWorkSessions: int = 0
		self._callLater: Optional[wx.CallLater] = None

	# ---- public state inspection -------------------------------------------------

	@property
	def phase(self) -> str:
		return self._phase

	@property
	def isPaused(self) -> bool:
		return self._pausedRemaining is not None

	@property
	def isRunning(self) -> bool:
		return self._phase != PHASE_IDLE and not self.isPaused

	@property
	def completedWorkSessions(self) -> int:
		return self._completedWorkSessions

	def remaining(self) -> float:
		"""Seconds remaining in the current phase, or 0 if idle."""
		if self._phase == PHASE_IDLE:
			return 0.0
		if self._pausedRemaining is not None:
			return self._pausedRemaining
		return max(0.0, self._phaseDuration - (time.time() - self._phaseStart))

	# ---- control ----------------------------------------------------------------

	def startOrResume(self) -> str:
		"""Start a fresh work phase if idle, resume if paused, otherwise pause.

		Returns one of: 'started', 'resumed', 'paused'.
		"""
		if self._phase == PHASE_IDLE:
			self._beginPhase(PHASE_WORK)
			return "started"
		if self.isPaused:
			self._resume()
			return "resumed"
		self._pause()
		return "paused"

	def stop(self) -> None:
		"""Stop the timer and clear all state including the session counter."""
		self._cancelCallLater()
		prev = self._phase
		self._phase = PHASE_IDLE
		self._pausedRemaining = None
		self._phaseStart = 0.0
		self._phaseDuration = 0.0
		self._completedWorkSessions = 0
		if prev != PHASE_IDLE:
			self._onPhaseChange(prev, PHASE_IDLE, self._completedWorkSessions)

	def skip(self) -> None:
		"""Skip the rest of the current phase and immediately advance."""
		if self._phase == PHASE_IDLE:
			return
		self._advance(skipped=True)

	def resetSessionCount(self) -> None:
		self._completedWorkSessions = 0

	# ---- internal ---------------------------------------------------------------

	def _beginPhase(self, phase: str) -> None:
		prev = self._phase
		durations = self._getDurations()
		if phase == PHASE_WORK:
			seconds = durations["workMinutes"] * 60.0
		elif phase == PHASE_SHORT_BREAK:
			seconds = durations["shortBreakMinutes"] * 60.0
		elif phase == PHASE_LONG_BREAK:
			seconds = durations["longBreakMinutes"] * 60.0
		else:
			seconds = 0.0
		self._phase = phase
		self._phaseStart = time.time()
		self._phaseDuration = seconds
		self._pausedRemaining = None
		self._scheduleEnd(seconds)
		self._onPhaseChange(prev, phase, self._completedWorkSessions)

	def _pause(self) -> None:
		if self._phase == PHASE_IDLE or self.isPaused:
			return
		self._pausedRemaining = self.remaining()
		self._cancelCallLater()

	def _resume(self) -> None:
		if not self.isPaused:
			return
		remaining = self._pausedRemaining or 0.0
		self._phaseStart = time.time() - (self._phaseDuration - remaining)
		self._pausedRemaining = None
		self._scheduleEnd(remaining)

	def _scheduleEnd(self, seconds: float) -> None:
		self._cancelCallLater()
		# wx.CallLater takes milliseconds. Clamp to >=1 so a zero-length phase still fires.
		ms = max(1, int(seconds * 1000))
		self._callLater = wx.CallLater(ms, self._onPhaseEnd)

	def _cancelCallLater(self) -> None:
		if self._callLater is not None:
			try:
				if self._callLater.IsRunning():
					self._callLater.Stop()
			except Exception:
				# Defensive: wx may have already torn the timer down.
				pass
			self._callLater = None

	def _onPhaseEnd(self) -> None:
		self._advance(skipped=False)

	def _advance(self, skipped: bool) -> None:
		"""Move from the current phase to the next phase in the pomodoro cycle."""
		durations = self._getDurations()
		current = self._phase
		# Count a completed work session only when the work phase ends naturally OR is skipped
		# (the user explicitly chose to advance — treat as done).
		if current == PHASE_WORK:
			self._completedWorkSessions += 1
			useLong = (
				self._completedWorkSessions % max(1, durations["sessionsBeforeLongBreak"]) == 0
			)
			nextPhase = PHASE_LONG_BREAK if useLong else PHASE_SHORT_BREAK
			autoStart = durations["autoStartBreaks"]
		else:
			nextPhase = PHASE_WORK
			autoStart = durations["autoStartWork"]

		self._cancelCallLater()
		if autoStart:
			self._beginPhase(nextPhase)
		else:
			# Park in idle state so the user can start the next phase manually.
			# We still announce the transition so the user knows what's next.
			prev = self._phase
			self._phase = PHASE_IDLE
			self._phaseStart = 0.0
			self._phaseDuration = 0.0
			self._pausedRemaining = None
			# Use a synthetic phase name for the announcement so the plugin knows
			# what's queued up next.
			self._onPhaseChange(prev, "ready:" + nextPhase, self._completedWorkSessions)
