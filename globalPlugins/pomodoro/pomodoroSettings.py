# Pomodoro Timer add-on for NVDA — settings panel.

from typing import Callable

import wx

import config
import gui
from gui.settingsDialogs import SettingsPanel

import addonHandler

addonHandler.initTranslation()
_: Callable[[str], str]


CONFIG_SECTION = "pomodoroTimer"


class PomodoroSettingsPanel(SettingsPanel):
	# Translators: title of the Pomodoro settings panel.
	title = _("Pomodoro Timer")

	def makeSettings(self, settingsSizer: wx.BoxSizer) -> None:
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		conf = config.conf[CONFIG_SECTION]

		# Translators: label for the work duration spinner in the Pomodoro settings panel.
		self.workCtrl = sHelper.addLabeledControl(
			_("&Work duration (minutes)"), wx.SpinCtrl, min=1, max=180, initial=conf["workMinutes"]
		)
		# Translators: label for the short break duration spinner.
		self.shortBreakCtrl = sHelper.addLabeledControl(
			_("&Short break duration (minutes)"), wx.SpinCtrl, min=1, max=60, initial=conf["shortBreakMinutes"]
		)
		# Translators: label for the long break duration spinner.
		self.longBreakCtrl = sHelper.addLabeledControl(
			_("&Long break duration (minutes)"), wx.SpinCtrl, min=1, max=120, initial=conf["longBreakMinutes"]
		)
		# Translators: label for the spinner controlling how many work sessions precede a long break.
		self.sessionsCtrl = sHelper.addLabeledControl(
			_("Work sessions &before a long break"),
			wx.SpinCtrl,
			min=1,
			max=20,
			initial=conf["sessionsBeforeLongBreak"],
		)
		# Translators: checkbox to automatically start breaks after work ends.
		self.autoStartBreaksCtrl = sHelper.addItem(
			wx.CheckBox(self, label=_("&Automatically start breaks when work ends"))
		)
		self.autoStartBreaksCtrl.SetValue(conf["autoStartBreaks"])
		# Translators: checkbox to automatically start the next work session after a break.
		self.autoStartWorkCtrl = sHelper.addItem(
			wx.CheckBox(self, label=_("Automatically start the &next work session when a break ends"))
		)
		self.autoStartWorkCtrl.SetValue(conf["autoStartWork"])
		# Translators: checkbox to play tones at phase transitions.
		self.playTonesCtrl = sHelper.addItem(
			wx.CheckBox(self, label=_("Play &tones at phase transitions"))
		)
		self.playTonesCtrl.SetValue(conf["playTransitionTone"])
		# Translators: checkbox to speak announcements at phase transitions.
		self.speakCtrl = sHelper.addItem(
			wx.CheckBox(self, label=_("S&peak announcements at phase transitions"))
		)
		self.speakCtrl.SetValue(conf["speakOnTransition"])
		# Translators: label for the spinner controlling periodic time-remaining reminders.
		self.tickIntervalCtrl = sHelper.addLabeledControl(
			_("Announce remaining time every (minutes, 0 = off)"),
			wx.SpinCtrl,
			min=0,
			max=30,
			initial=conf["tickIntervalMinutes"],
		)
		# Translators: checkbox to play a soft tone alongside the periodic time-remaining announcement.
		self.playTickToneCtrl = sHelper.addItem(
			wx.CheckBox(self, label=_("Play a short t&one with the periodic time-remaining announcement"))
		)
		self.playTickToneCtrl.SetValue(conf["playTickTone"])

	def onSave(self) -> None:
		conf = config.conf[CONFIG_SECTION]
		conf["workMinutes"] = self.workCtrl.GetValue()
		conf["shortBreakMinutes"] = self.shortBreakCtrl.GetValue()
		conf["longBreakMinutes"] = self.longBreakCtrl.GetValue()
		conf["sessionsBeforeLongBreak"] = self.sessionsCtrl.GetValue()
		conf["autoStartBreaks"] = self.autoStartBreaksCtrl.GetValue()
		conf["autoStartWork"] = self.autoStartWorkCtrl.GetValue()
		conf["playTransitionTone"] = self.playTonesCtrl.GetValue()
		conf["speakOnTransition"] = self.speakCtrl.GetValue()
		conf["tickIntervalMinutes"] = self.tickIntervalCtrl.GetValue()
		conf["playTickTone"] = self.playTickToneCtrl.GetValue()
