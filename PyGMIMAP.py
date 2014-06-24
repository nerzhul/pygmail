#! /usr/bin/python2.7

class PyGMIMAPMgr:
	_imapservers = {}
	_sqlMgr = None
	
	_IMAPAccountsTable = "accounts"
	
	def __init__(self,sqlMgr):
		self._sqlMgr = sqlMgr
		
	def getIMAPServers(self):
		print self._sqlMgr.Fetch("SELECT acctid, acctlabel, imapserver, imapport FROM %s" % self._IMAPAccountsTable)
