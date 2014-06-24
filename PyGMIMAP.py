#! /usr/bin/python2.7

import PyGMSQL

class PyGMIMAPMgr:
	_imapServers = {}
	_sqlMgr = None
	
	_IMAPAccountsTable = "imapaccounts"
	
	def __init__(self,sqlMgr):
		self._sqlMgr = sqlMgr
		self._imapServers = {}
		
	def getIMAPServers(self):
		for row in self._sqlMgr.Fetch("SELECT acctid, acctlabel, serveraddr, serverport FROM %s" % self._IMAPAccountsTable):
			print row


class IMAPServer(PyGMSQL.PyGMDBObj):
	_id = 0
	_label = ""
	_serverAddr = ""
	_serverPort = 143
	_ssl = False
	_serverCredentials = ""
	_serverPwd = ""
	_sqlCredentialsTable = "imapcredentials"
	
	def __init__(self,sqlMgr):
		PyGMSQL.PyGMDBObj.__init__(self,sqlMgr)
		self._sqlTable = "imapaccounts"
		self._idName = "acctid"
		
	def CreateTable(self):
		ret = 0
		try:
			self._sqlMgr.ExecQuery("CREATE TABLE %s(%s INTEGER PRIMARY KEY AUTOINCREMENT, acctlabel VARCHAR(64), login VARCHAR(128), serveraddr VARCHAR(128), serverport INTEGER, serverssl INTEGER)" % (self._sqlTable, self._idName))
			ret = 0
		except:
			ret = 4
		
		if ret != 0:
			return ret
		
		ret = 0
		try:
			self._sqlMgr.ExecQuery("CREATE TABLE %s(%s INTEGER PRIMARY KEY AUTOINCREMENT, imappwd VARCHAR(2048))" % (self._sqlCredentialsTable,self._idName))
			ret = 0
		except:
			ret = 4
		
		if ret != 0:
			return ret
		
