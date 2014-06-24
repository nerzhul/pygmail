#! /usr/bin/python2.7

import sqlite3

from PyGMConfig import PyGMailConfig

class PyGMSQLiteMgr:
	_conn = None
	_cursor = None
	
	def __init__(self):
		_conn = None
	
	def Connect(self):
		try:
			self._conn = sqlite3.connect(PyGMailConfig.userDBPath)
			self._cursor = self._conn.cursor()
			return self.CheckTables()
		except Exception, e:
			self._conn = None
			return 1
	
	def CheckTables(self):
		# Check DB consistency
		ret = self.CreateTableIfNotExists("accounts","acctid")
		if ret != 0:
			return ret
			
		return 0
		
	def CreateTableIfNotExists(self,tablename,field):
		try:
			self._cursor.execute('SELECT %s FROM %s' % (field,tablename))
			return 0
		except Exception, e:
			try:
				if tablename == "accounts":
					self._cursor.execute("CREATE TABLE accounts(acctid INTEGER PRIMARY KEY AUTOINCREMENT,acctlabel VARCHAR(64), imapserver VARCHAR(128), imapport INT, imappasswd VARCHAR(4096))")
				else:
					return 4
				return 0
			except Exception, e:
				print e
				return 3
				
			return 2
	
	def Fetch(self, request, values = None):
		if values != None:
			self._cursor.execute(request, values)
		else:
			self._cursor.execute(request)
		return self._cursor.fetchall()
	
	def FetchOne(self, request, values = None):
		if values != None:
			self._cursor.execute(request, values)
		else:
			self._cursor.execute(request)
		return self._cursor.fetchone()
