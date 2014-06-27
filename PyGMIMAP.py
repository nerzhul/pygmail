#! /usr/bin/python2.7

import imaplib
import PyGMSQL, PyGMThread

class PyGMIMAPMgr(PyGMThread.Thread):
	_imapServers = {}
	_sqlMgr = None
	
	_IMAPAccountsTable = "imapaccounts"
	
	def __init__(self):
		PyGMThread.Thread.__init__(self)
		# Thread options
		self.sleepingTimer = 60
		
		self._sqlMgr = None
		self._imapServers = {}
	
	def run(self):
		self.launchMsg()
		
		# Connect to SQLite DB
		self._sqlMgr = PyGMSQL.PyGMSQLiteMgr()
		self._sqlMgr.Connect()
		
		while True:
			self.setRunning(True)
			self.loadIMAPServers()
			self.setRunning(False)
		
	def loadIMAPServers(self):
		for row in self._sqlMgr.Fetch("SELECT acctid FROM %s" % self._IMAPAccountsTable):
			if row[0] not in self._imapServers:
				self._imapServers[row[0]] = IMAPServer(self._sqlMgr)
				
			self._imapServers[row[0]].Load(row[0])
			self._imapServers[row[0]].Connect()
			self._imapServers[row[0]].Login()


class IMAPServer(PyGMSQL.PyGMDBObj):
	# DB associated attributes
	_id = 0
	_label = ""
	_serverAddr = ""
	_serverPort = 143
	_ssl = False
	_userName = ""
	_sqlCredentialsTable = "imapcredentials"
	
	# imap4 objects
	_imapConn = None
	
	# status
	_logged = False
	
	def __init__(self,sqlMgr):
		PyGMSQL.PyGMDBObj.__init__(self,sqlMgr)
		self._sqlTable = "imapaccounts"
		self._idName = "acctid"
		self._imapConn = None
		self._logged = False
		
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
			
	def Load(self,serverId):
		res = self._sqlMgr.FetchOne("SELECT acctlabel, login, serveraddr, serverport, serverssl FROM %s WHERE %s = %s" % (self._sqlTable, self._idName, serverId))
		
		self._id = serverId
		self._label = res[0]
		self._userName = res[1]
		self._serverAddr = res[2]
		self._serverPort = res[3]
		
		if res[4] > 0:
			self._ssl = True
		else:
			self._ssl = False
	
	def Connect(self):
		try:
			if self._ssl == False:
				self._imapConn = imaplib.IMAP4(self._serverAddr)
			else:
				self._imapConn = imaplib.IMAP4_SSL(self._serverAddr)
			
			self._logged = False
			return 0
		except imaplib.IMAP4.error, e:
			print e
			return 1
	
	def Login(self):
		if self._imapConn == None:
			return 1
		
		# Now we get the user passwd from DB
		res = self._sqlMgr.FetchOne("SELECT imappwd FROM %s WHERE %s = %s" % (self._sqlCredentialsTable, self._idName, self._id))
		
		if res == None:
			return 2
		
		try:
			self._imapConn.login(self._userName,res[0])
			self._logged = True
			return 0
		except imaplib.IMAP4.error, e:
			return 3
		
	def collectMailboxes(self):
		if self._imapConn == None and self._logged == False:
			return 1
		
		
		
