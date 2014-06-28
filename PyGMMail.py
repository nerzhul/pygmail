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

class PyGMEmail:
	_mail = None
	
	# encoding
	_foundEncodingModes = ()
	# decoded attributes
	_decodedSubject = None
	_decodedFrom = None
	
	def __init__(self,rawMail):
		self._mail = email.message_from_string(rawMail)

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
	
	def getDate(self):
		return self._mail["Date"]
		
	def reencodeStringToUTF8(self,_str,_dec):
		return _str.decode(_dec).encode('utf-8')
