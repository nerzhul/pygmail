#! /usr/bin/python2.7

import imaplib, re, time
import PyGMSQL, PyGMThread

class IMAPTreeViewType():
	account = 1
	mailBox = 2

class PyGMIMAPMgr(PyGMThread.Thread):
	_imapServers = {}
	_sqlMgr = None
	_mainWin = None
	
	_IMAPAccountsTable = "imapaccounts"
	
	def __init__(self):
		PyGMThread.Thread.__init__(self)
		# Thread options
		self.sleepingTimer = 60
		
		self._sqlMgr = None
		self._imapServers = {}
		
	def setMainWindow(self,win):
		self._mainWin = win
	
	def run(self):
		self.launchMsg()
		
		# Connect to SQLite DB
		self._sqlMgr = PyGMSQL.PyGMSQLiteMgr()
		self._sqlMgr.Connect()
		
		# We need to wait the mainWindow to be ready
		while self._mainWin.isWindowReady() == False:
			time.sleep(1)
			
		while True:
			self.setRunning(True)
			self.loadIMAPServers()
			self.setRunning(False)
		
	def loadIMAPServers(self):
		for row in self._sqlMgr.Fetch("SELECT acctid FROM %s" % self._IMAPAccountsTable):
			serverId = row[0]
			imapServer = None
			if serverId not in self._imapServers:
				self._imapServers[serverId] = IMAPServer(self._sqlMgr)
				
			imapServer = self._imapServers[serverId]
				
			imapServer.Load(serverId)
			if imapServer.Connect() == 0:
				if imapServer.Login() == 0:
					if self.findAccountInTreeView(serverId) == None:
						serverIter = self._mainWin.addElemToMBTreeView(None,[imapServer._serverAddr,IMAPTreeViewType.account,"%s" % serverId])
						self.renderMailboxes(imapServer,serverIter)
						
	def findAccountInTreeView(self,acctid):
		store = self._mainWin.getMailboxGTKStore()
		
		mbtsIter = store.get_iter_first()
		while mbtsIter != None:
			if store[mbtsIter][1] == IMAPTreeViewType.account and store[mbtsIter][2] == acctid:
				return store[mbtsIter]
			
			mbtsIter = store.iter_next(mbtsIter)
		
		return None
		
	def findMailBoxInTreeView(self,mbPath):
		store = self._mainWin.getMailboxGTKStore()
		mbIter = store.get_iter_first()
		return self.findMailBoxTreeIter(store,mbIter,mbPath)
		
	def findMailBoxTreeIter(self,store,mbIter,mbPath):
		while mbIter != None:
			iterFound = None
			
			iterChild = store.iter_children(mbIter)
			if iterChild != None:
				iterFound = self.findMailBoxTreeIter(store,iterChild,mbPath)
				
			if iterFound == None:
				iterFound = mbIter
			
			if store[iterFound][1] == IMAPTreeViewType.mailBox and store[iterFound][2] == mbPath:
				return iterFound
			
			mbIter = store.iter_next(mbIter)
		
		return None
			
	def renderMailboxes(self,imapServer,serverIter):
		mbList = imapServer.collectMailboxes()
		
		# buffer which say the already rendered mailboxes, for perf improvements
		renderedMailboxes = ()
		for mb in mbList:
			mb = re.split(" \".\" ",mb)
			mbPath = re.sub("\"","",mb[1])
			mbSpl = re.split("\.",mbPath)
			mbSplLen = len(mbSpl)
			
			# render mailbox and its parents (if not already rendered)
			for mbNameIdx in range(0,mbSplLen):
				mbName = mbSpl[mbNameIdx]
				
				# generate MbPath
				mbPathTmp = ""
				for idx2 in range(0,mbNameIdx+1):
					mbPathTmp += mbSpl[idx2]
					if idx2 != mbNameIdx:
						mbPathTmp += "."
				
				# generate parent MbPath
				mbPathParentTmp = ""
				for idx2 in range(0,mbNameIdx):
					mbPathParentTmp += mbSpl[idx2]
					if idx2 != mbNameIdx-1:
						mbPathParentTmp += "."
				
				uniqPath = "%s-%s" % (imapServer._serverAddr, mbPathTmp)
				uniqParentPath = "%s-%s" % (imapServer._serverAddr, mbPathParentTmp)
				if uniqPath not in renderedMailboxes:
					mbIter = self.findMailBoxInTreeView(uniqPath)
					
					# If there is a parent name, search, else set to serverIter (the account)
					if mbPathParentTmp != "":
						mbIterParent = self.findMailBoxInTreeView(uniqParentPath)
					else:
						mbIterParent = serverIter
						
					if mbIter == None:
						self._mainWin.addElemToMBTreeView(mbIterParent,[mbName,IMAPTreeViewType.mailBox,uniqPath])
						renderedMailboxes += (uniqPath,)
		
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
		self.myName = "IMAPServer"
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
			self.logCritical(e)
			return 1
	
	def Login(self):
		if self._imapConn == None:
			return 1
		
		# Now we get the user passwd from DB
		res = self._sqlMgr.FetchOne("SELECT imappwd FROM %s WHERE %s = %s" % (self._sqlCredentialsTable, self._idName, self._id))
		
		if res == None:
			self.logCritical("No password found for server %s (id %s)" % (self._serverAddr,self._id))
			return 2
		
		try:
			self._imapConn.login(self._userName,res[0])
			self._logged = True
			return 0
		except imaplib.IMAP4.error, e:
			self.logWarn(e)
			return 3
		
	def collectMailboxes(self):
		if self._imapConn == None and self._logged == False:
			self.logCritical("Trying to collect mailbox on non connected/logged server %s (id %s)" % (self._serverAddr,self._id))
			return None
		
		mbList = self._imapConn.list()
		
		if mbList[0] != "OK":
			self.logCritical("Server %s (id %s) returned %s when collecting mailboxes" % (self._serverAddr,self._id, mbList[0]))
			return None
		
		return mbList[1]
		
