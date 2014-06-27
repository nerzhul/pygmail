# -*- coding: utf-8 -*-

"""
* Copyright (C) 2010-2014 Loïc BLOT, UNIX Experience <http://www.unix-experience.fr/>
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import threading, logging, datetime, time

class Thread(threading.Thread):
	# sub thread counter
	threadCounterMutex = threading.Lock()
	threadCounter = 0
	max_threads = 30
	
	# For threading sync
	runStatus = False
	runningMutex = threading.Lock()
	runStartTime = 0

	# Timers
	sleepingTimer = 0
	startTimer = 0
	
	# Naming
	logger = None
	myName = "UNK-Thread-Name"

	def __init__(self):
		threading.Thread.__init__(self)
		self.logger = logging.getLogger("PyGMail")

	# Thread numbering
	
	def incrThreadNb(self):
		self.threadCounterMutex.acquire()
		self.threadCounter += 1
		self.threadCounterMutex.release()

	def decrThreadNb(self):
		self.threadCounterMutex.acquire()
		self.threadCounter = self.threadCounter - 1
		self.threadCounterMutex.release()

	def getThreadNb(self):
		val = 0
		self.threadCounterMutex.acquire()
		val = self.threadCounter
		self.threadCounterMutex.release()
		return val
	
	# Running states 
	
	def setRunning(self,runStatus):
		self.runningMutex.acquire()
		self.runStatus = runStatus
		self.runningMutex.release()
		
		if runStatus == True:
			self.runStartTime = datetime.datetime.now()
			self.startMsg()
		else:
			self.endMsg()
			time.sleep(self.sleepingTimer)
		
	def isRunning(self):
		rs = True
		self.runningMutex.acquire()
		rs = self.runStatus
		self.runningMutex.release()
		return rs

	# Service messages
	
	def launchMsg(self):
		self.logger.info("%s launched" % self.myName)
		
	def startMsg(self):
		self.logger.info("%s started" % self.myName)
	
	def endMsg(self):
		totaltime = datetime.datetime.now() - self.runStartTime 
		self.logger.info("%s done (time: %s)" % (self.myName,totaltime))
	
	def logDebug(self, msg):
		self.logger.debug("%s: %s" % (self.myName,msg))
	
	def logInfo(self, msg):
		self.logger.info("%s: %s" % (self.myName,msg))

	def logWarn(self, msg):
		self.logger.warn("%s: %s" % (self.myName,msg))
		
	def logError(self, msg):
		self.logger.error("%s: %s" % (self.myName,msg))

	def logCritical(self, msg):
		self.logger.critical("%s: %s" % (self.myName,msg))
