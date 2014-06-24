#! /usr/bin/python2.7

import sqlite3

from PyGMConfig import PyGMailConfig

class PyGMDBObj:
	_sqlMgr = None
	_sqlTable = ""
	_idName = ""
	
	def __init__(self,sqlMgr):
		self._sqlMgr = sqlMgr
		self._sqlTable = ""
		self._idName = ""
		
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

class PyGMSQLiteMgr:
	_conn = None
	_cursor = None
	
	def __init__(self):
		_conn = None
	
	def Connect(self):
		try:
			self._conn = sqlite3.connect(PyGMailConfig.userDBPath)
			self._cursor = self._conn.cursor()
			ret = self.CheckTables()
			return ret
		except Exception, e:
			self._conn = None
			return 1
	
	# Check DB
	def CheckTables(self):
		# import all needed objects
		from PyGMIMAP import IMAPServer
		
		# Now iterate and create the missing tables
		sqlObjs = [IMAPServer(self)]
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
		print "test"
		self._conn.commit()

