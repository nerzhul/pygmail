#! /usr/bin/python2.7

class PyGMailConfig:
	appName = "PyGMail"
	appVersion = "0.0.4"
	userDBPath = "~/.local/pygmail.sqlite"
	
	@staticmethod
	def getAppNameAndVersion():
		return "%s (%s)" % (PyGMailConfig.appName,PyGMailConfig.appVersion)
