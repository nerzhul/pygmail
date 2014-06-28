#! /usr/bin/python2.7

import sqlite3, logging, os.path

from PyGMConfig import PyGMailConfig

class PyGMDBObj:
	_sqlMgr = None
	_sqlTable = ""
	_idName = ""
	myName = "UNK-DBOBj-NAME"
	
	def __init__(self,sqlMgr):
		self._sqlMgr = sqlMgr
		self._sqlTable = ""
		self._idName = ""
		self.logger = logging.getLogger("PyGMail")
		
	def CreateTable(self):
		print "Method not implemented"
		return 99
		
	def CreateTableIfNotExists(self):
		try:
			self._sqlMgr._cursor.execute('SELECT %s FROM %s' % (self._idName,self._sqlTable))
			return 0
		except Exception, e:
			try:
				return self.CreateTable()
			except Exception, e:
				print e
				return 3
				
			return 2
	
	def Load(self,objId):
		print "Method not implemented"
		return 99
	
	def Save(self):
		print "Method not implemented"
		return 99
		
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


class PyGMSQLiteMgr:
	_conn = None
	_cursor = None
	
	def __init__(self):
		_conn = None
	
	def Connect(self):
		try:
			self._conn = sqlite3.connect(os.path.expanduser(PyGMailConfig.userDBPath))
			self._cursor = self._conn.cursor()
			ret = self.CheckTables()
			return ret
		except Exception, e:
			print e
			self._conn = None
			return 1
	
	# Check DB
	def CheckTables(self):
		# import all needed objects
		from PyGMIMAP import IMAPServer
		from PyGMMail import PyGMEmail
		
		# Now iterate and create the missing tables
		sqlObjs = [IMAPServer(self),PyGMEmail("",self)]
		for obj in sqlObjs:
			ret = obj.CreateTableIfNotExists()
			if ret != 0:
				return ret
		
		# Commit modifications
		self.Commit()
		return 0
			
	def ExecQuery(self, request, values = None):
		if values != None:
			self._cursor.execute(request, values)
		else:
			self._cursor.execute(request)
	
	def Fetch(self, request, values = None):
		self.ExecQuery(request,values)
		return self._cursor.fetchall()
	
	def FetchOne(self, request, values = None):
		self.ExecQuery(request,values)
		return self._cursor.fetchone()

	def Commit(self):
		self._conn.commit()
		
	def close(self):
		if self._conn:
			self._conn.close()

