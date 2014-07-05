# -*- coding: utf-8 -*-

"""
* Copyright (C) 2014 Loïc BLOT, UNIX Experience <http://www.unix-experience.fr/>
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

import imaplib, re, time, email, email.header
import PyGMSQL, PyGMThread, PyGMMail

class IMAPTreeViewType():
	account = 1
	mailBox = 2

class IMAPMailState():
	FRESH = "mail-message-new"
	READ = "mail-mark-read"
	ANSWERED = "mail-reply-sender"
	READ_ANSWERED = "mail-reply-sender"

class PyGMIMAPMgr(PyGMThread.Thread):
	_imapServers = {}
	_sqlMgr = None
	_mainWin = None
	_actionName = ""
	_actionArgs = {}
	
	_IMAPAccountsTable = "imapaccounts"
	
	def __init__(self,actName,actArgs = {}):
		PyGMThread.Thread.__init__(self)
		self._sqlMgr = None
		self._imapServers = {}
		self._actionName = actName
		self._actionArgs = actArgs
		
	def setMainWindow(self,win):
		self._mainWin = win
	
	def run(self):
		self.launchMsg()
		
		# We need to wait the mainWindow to be ready
		while self._mainWin.isWindowReady() == False:
			time.sleep(1)
		
		if self._actionName == "load-mailboxes":
			self.loadMailBoxes()
		elif self._actionName == "load-maillist":
			self.loadMailboxMails(self._actionArgs["serverid"],self._actionArgs["mailbox"])
		elif self._actionName == "load-mail":
			mailObj = self.loadMail(self._actionArgs["serverid"],self._actionArgs["mailbox"],self._actionArgs["mailid"])
			self._mainWin.setMailViewText(mailObj.getBody(),mailObj.isHTML)
		
	def loadMailBoxes(self):
		# Connect to SQLite DB
		self._sqlMgr = PyGMSQL.PyGMSQLiteMgr()
		self._sqlMgr.Connect()
		
		self._mainWin.setFooterText("Loading mailboxes")
		
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
		
		self._mainWin.removeFooterText()
		self._sqlMgr.close()
	
	def loadMailboxMails(self,serverId,mbName):
		# Connect to SQLite DB
		self._sqlMgr = PyGMSQL.PyGMSQLiteMgr()
		self._sqlMgr.Connect()
		
		self._mainWin.setFooterText("Loading mails from mailbox %s" % mbName)
		
		imapServer = None
		if serverId not in self._imapServers:
			self._imapServers[serverId] = IMAPServer(self._sqlMgr)
		
		imapServer = self._imapServers[serverId]
		if imapServer.Load(serverId) == 0 and imapServer.Connect() == 0 and imapServer.Login() == 0:
			mailList = imapServer.getMailHeadersFromMailbox(mbName)
			
			# we clear the treeview only if connection to server succeed
			self._mainWin.clearMLTreeView()
			
			# Now we get the mails and store it into our mailList
			for mailId in mailList:
				# Load mail 
				emailMsg = PyGMMail.PyGMEmail(mailList[mailId]["data"],self._sqlMgr)
				emailMsg._mailId = mailId
				emailMsg._mailbox = mbName
				emailMsg._serverId = serverId
				
				readAnsweredState = IMAPMailState().FRESH
				if "\Seen" in mailList[mailId]["flags"]:
					if "\Answered" in mailList[mailId]["flags"]:
						readAnsweredState = IMAPMailState().READ_ANSWERED
					else:
						readAnsweredState = IMAPMailState().READ
				urgentState = 0
				if "\Flagged" in mailList[mailId]["flags"]:
					urgentState = 1
				
				mailIter = self._mainWin.addElemToMLTreeView(None,["%s" % readAnsweredState,urgentState,emailMsg.getFrom(),emailMsg.getSubject(),emailMsg.getDate(),mailId,mbName,serverId])
				#emailMsg.Save()
		
		self._mainWin.removeFooterText()
		self._sqlMgr.close()
	
	def loadMail(self,serverId,mbName,mailId):
		# Connect to SQLite DB
		self._sqlMgr = PyGMSQL.PyGMSQLiteMgr()
		self._sqlMgr.Connect()
		
		res = None
		
		imapServer = None
		if serverId not in self._imapServers:
			self._imapServers[serverId] = IMAPServer(self._sqlMgr)
		
		imapServer = self._imapServers[serverId]
		
		self._mainWin.setFooterText("Loading mail %s from mailbox %s" % (mailId,mbName))
		
		if imapServer.Load(serverId) == 0 and imapServer.Connect() == 0 and imapServer.Login() == 0:
			mailList = imapServer.getMailsFromMailbox(mbName,mailId)
			emailMsg = PyGMMail.PyGMEmail(mailList[mailId]["data"],self._sqlMgr)
			emailMsg._mailId = mailId
			emailMsg._mailbox = mbName
			emailMsg._serverId = serverId
			res = emailMsg
			
		self._mainWin.removeFooterText()
		self._sqlMgr.close()
		
		return res
			
	def findAccountInTreeView(self,acctid):
		store = self._mainWin.getMailboxGTKStore()
		
		if store == None:
			return None
			
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
				
				uniqPath = "%s-%s" % (imapServer._id, mbPathTmp)
				uniqParentPath = "%s-%s" % (imapServer._id, mbPathParentTmp)
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
		try:
			res = self._sqlMgr.FetchOne("SELECT acctlabel, login, serveraddr, serverport, serverssl FROM %s WHERE %s = %s" % (self._sqlTable, self._idName, serverId))
		except:
			return 1
		
		self._id = serverId
		self._label = res[0]
		self._userName = res[1]
		self._serverAddr = res[2]
		self._serverPort = res[3]
		
		if res[4] > 0:
			self._ssl = True
		else:
			self._ssl = False
		
		return 0
	
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
	
	def getMailsFromMailbox(self,mbName,uidList = None,fetchOptions = None):
		try:
			self._imapConn.select(mbName)
		except imaplib.IMAP4.error, e:
			self.logCritical(e)
			return None

		imapFilter = "ALL"
		
		if uidList != None:
			imapFilter = "(UID %s)" % uidList
		
		result, data = self._imapConn.uid('search', None, imapFilter)
		if result != "OK":
			self.logCritical("getMailsFromMailbox returned %s" % result)
			return None
		
		mailIdList = data[0].split()

		mailList = {}
		for mailId in mailIdList:
			# If filter is set to false, only get headers
			if fetchOptions == None:
				fetchOptions = "(FLAGS BODY.PEEK[])"
			
			result, data = self._imapConn.uid('fetch', mailId, fetchOptions)
			if result != "OK":
				self.logCritical("getMailsFromMailbox. Fetching mailid %s returned %s" % (mailId,result))
			else:
				imapFlagsFound = re.search("FLAGS \((.*)\) ",data[0][0])
				if imapFlagsFound != None:
					imapFlagsFound = re.sub("FLAGS \(","",imapFlagsFound.group(0))
					imapFlagsFound = re.sub("\) ","",imapFlagsFound)
					imapFlagsFound = re.split(" ",imapFlagsFound)
				mailList[mailId] = {"data": data[0][1], "flags": imapFlagsFound}
		
		return mailList

	"""
	getMailsFromMailbox helpers
	"""
	
	def getMailHeadersFromMailbox(self,mbName,uidList = None):
		return self.getMailsFromMailbox(mbName,uidList,"(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
