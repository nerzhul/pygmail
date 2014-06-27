#! /usr/bin/python2.7

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
