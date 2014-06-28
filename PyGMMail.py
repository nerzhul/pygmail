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

import email, email.header
import PyGMSQL

class PyGMEmail(PyGMSQL.PyGMDBObj):
	_mail = None
	
	# Administrative attributes
	_mailId = 0
	_mailbox = ""
	_serverId = 0
	
	# encoding
	_foundEncodingModes = ()
	# decoded attributes
	_decodedSubject = None
	_decodedFrom = None
	_decodedTo = None
	_decodedDate = None
	_decodedBody = None
	
	def __init__(self,rawMail,sqlMgr):
		PyGMSQL.PyGMDBObj.__init__(self,sqlMgr)
		self.myName = "PyGMEmail"
		self._sqlTable = "email"
		self._idName = "mailid"
		
		self._mail = email.message_from_string(rawMail)
		
	"""
	database actions
	"""
		
	def CreateTable(self):
		try:
			self._sqlMgr.ExecQuery("CREATE TABLE %s(%s INTEGER, mailbox VARCHAR(256), serverId INTEGER , mailfrom TEXT, mailto TEXT, mailsubject TEXT, mailbody TEXT, maildate VARCHAR(64), PRIMARY KEY(%s,mailbox,serverId))" % (self._sqlTable, self._idName, self._idName))
			return 0
		except Exception, e:
			print e
			return 4
	
	def Save(self):
		try:
			vals = (self._mailId, self._mailbox, self._serverId)
			self._sqlMgr.ExecQuery("DELETE FROM %s WHERE %s = ? AND mailbox = ? AND serverId = ?" % (self._sqlTable, self._idName), vals)
			
			vals = (self._mailId, self._mailbox, self._serverId, self.getFrom().decode('utf-8'), self.getTo().decode('utf-8'), self.getSubject().decode('utf-8'), self.getBody().decode('utf-8'), self.getDate().decode('utf-8'))
			self._sqlMgr.ExecQuery("INSERT INTO %s(%s,mailbox,serverId,mailfrom,mailto,mailsubject,mailbody,maildate) VALUES (?,?,?,?,?,?,?,?)" % (self._sqlTable, self._idName), vals)
			
			self._sqlMgr.Commit()
			return 0
		except Exception, e:
			print e
			return 4
	
	def Load(self,mailId,mboxName,serverId):
		try:
			vals = (mailId,mboxName,serverId)
			res = self._sqlMgr.FetchOne("SELECT mailfrom,mailto,mailsubject,mailbody,maildate FROM %s WHERE %s = ? AND mailbox = ? AND serverId = ?" % (self._sqlTable, self._idName), vals)
		except Exception, e:
			print e
			return 1
			
		self._mailId = mailId
		self._mailbox = mboxName
		self._serverId = serverId
		self._decodedFrom = res[0].encode('utf-8')
		self._decodedTo = res[1].encode('utf-8')
		self._decodedSubject = res[2].encode('utf-8')
		self._decodedBody = res[3].encode('utf-8')
		self._decodedDate = res[4].encode('utf-8')
		
		return 0
		
	"""
	raw email decoding
	"""

	def getSubject(self):
		if self._decodedSubject == None:
			self._decodedSubject = ""
			
			decHeader = email.header.decode_header(self._mail["Subject"])
			
			for row in decHeader:
				self._decodedSubject += "%s " % self.reencodeStringToUTF8(row[0], row[1] or 'utf-8')
				if row[1] not in self._foundEncodingModes:
					self._foundEncodingModes += (row[1],)
			
		return self._decodedSubject

	def getFrom(self):
		if self._decodedFrom == None:
			self._decodedFrom = ""
			
			decHeader = email.header.decode_header(self._mail["From"])
			for row in decHeader:
				self._decodedFrom += self.reencodeStringToUTF8(row[0], row[1] or 'utf-8')
				if row[1] not in self._foundEncodingModes:
					self._foundEncodingModes += (row[1],)
			
		return self._decodedFrom
	
	def getTo(self):
		if self._decodedTo == None:
			self._decodedTo = ""
			
			decHeader = email.header.decode_header(self._mail["To"])
			for row in decHeader:
				self._decodedTo += self.reencodeStringToUTF8(row[0], row[1] or 'utf-8')
				if row[1] not in self._foundEncodingModes:
					self._foundEncodingModes += (row[1],)
			
		return self._decodedTo
	
	def getDate(self):
		if self._decodedDate == None:
			self._decodedDate = self._mail["Date"]
		return self._decodedDate
		
	def getBody(self):
		if self._decodedBody == None:
			self._decodedBody = ""
			
			if self._mail.is_multipart():
				for part in self._mail.get_payload():
					charset = part.get_content_charset()
					payload = part.get_payload(decode=True)
					
					if charset is None and payload != None:
						self._decodedBody += payload
					elif part.get_content_type() == 'text/plain':
						 self._decodedBody += self.reencodeStringToUTF8(payload, charset or 'utf-8')
					elif part.get_content_type() == 'text/html':
						self._decodedBody += self.reencodeStringToUTF8(payload, charset or 'utf-8')
			else:
				charset = self._mail.get_content_charset()
				payload = self._mail.get_payload(decode=True)
				
				if charset is None and self._mail.get_payload(decode=True) != None:
					self._decodedBody += payload
				elif self._mail.get_content_type() == 'text/plain':
					 self._decodedBody += self.reencodeStringToUTF8(payload, charset or 'utf-8')
				elif self._mail.get_content_type() == 'text/html':
					self._decodedBody += self.reencodeStringToUTF8(payload, charset or 'utf-8')
		
		return self._decodedBody
		
	def reencodeStringToUTF8(self,_str,_dec):
		return _str.decode(_dec).encode('utf-8')
