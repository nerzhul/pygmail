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

from gi.repository import Gtk, Gio
from PyGMConfig import PyGMailConfig
from PyGMIMAP import PyGMIMAPMgr
import PyGMMail
import threading, re
import GnomeHTMLTextView

class MainWindowMgr():
	# Interface stores
	_builder = None
	_window = None
	_headerBar = None
	
	# mailbox list
	_mailboxTreeView = None
	mbTreeViewLock = threading.Lock()
	
	# mail list
	_maillistListView = None
	mlTreeViewLock = threading.Lock()
	
	# mail view
	_mailTextView = None
	mTextViewLock = threading.Lock()
	
	# footer
	_footerBar = None
	footerLock = threading.Lock()
	
	# Status of the GTK window
	readyLock = threading.Lock()
	isReady = False
	
	_sqlMgr = None
	_toKillThreads = []
	
	def __init__(self,builder,window,sqlMgr):
		self._builder = builder
		self._window = window
		self._sqlMgr = sqlMgr
		
		# Init mutexes
		self.readyLock = threading.Lock()
		self.mbTreeViewLock = threading.Lock()
		self.mlTreeViewLock = threading.Lock()
		self.mTextViewLock = threading.Lock()
		self.footerLock = threading.Lock()

		# Window options
		self._window.set_title(PyGMailConfig.getAppNameAndVersion())
		self._window.set_border_width(10)
		self._window.set_default_size(800, 400)

		# First, create the header bar
		self.createHeaderBar()

		# Now the component grid
		self._footerBar = self._builder.get_object("mwStatusBar")

		self.setFooterText("Initialization in progress...")

		self.createMailboxTreeView()
		self.createMaillistTreeView()
		self.createMailView()

		# Events
		self._window.connect("delete-event", self.closeWindow)

		# Complete
		self._footerBar.show()
		self.setFooterText("Initialization complete")
		
		self.readyLock.acquire()
		self.isReady = True
		self.readyLock.release()

	def closeWindow(self,_window,_event):
		self.killAllRunningThreads()
		Gtk.main_quit
	
	# We bufferize pointer to running threads
	def addThreadToKill(self,thread):
		if thread not in self._toKillThreads:
			self._toKillThreads +=  [thread,]

	# When main windows is closed, we need to kill all threads
	def killAllRunningThreads(self):
		for thread in self._toKillThreads:
			thread._Thread__stop()
	
	"""
	Footer bar
	"""
	
	def setFooterText(self,_text):
		self.footerLock.acquire()
		context = self._footerBar.get_context_id("PyGMail")
		self._footerBar.pop(context)
		self._footerBar.push(context, "%s" % _text)
		self.footerLock.release()
	
	def removeFooterText(self):
		self.footerLock.acquire()
		context = self._footerBar.get_context_id("PyGMail")
		self._footerBar.pop(context)
		self.footerLock.release()
		
	"""
	Mailbox Treeview
	"""
	
	def getMailboxGTKStore(self):
		self.mbTreeViewLock.acquire()
		model = self._mailboxTreeView.get_model()
		self.mbTreeViewLock.release()
		return model
	
	def createMailboxTreeView(self):
		# TreeStore(Label,LeafType,Value (serverId or real IMAP Path))
		mailboxTreeStore = Gtk.TreeStore(str,int,str)

		self.mbTreeViewLock.acquire()
		self._mailboxTreeView = self._builder.get_object("mailboxTreeView")
		self._mailboxTreeView.set_model(mailboxTreeStore)
		
		# Table columns
		renderer = Gtk.CellRendererText()
		mbTreeViewCol = Gtk.TreeViewColumn("Boîte de réception", renderer, text=0)
		self._mailboxTreeView.append_column(mbTreeViewCol)
		
		# Event handler
		select = self._mailboxTreeView.get_selection()
		select.connect("changed", self.onMailboxSelectionChanged)
		
		self.mbTreeViewLock.release()

	def onMailboxSelectionChanged(self,selection):
		model, treeiter = selection.get_selected()
		mbSplit = re.split("-",model[treeiter][2])
		
		if len(mbSplit) >= 2:
			serverId = mbSplit[0]
			mbName = ""
			for idx in range(1,len(mbSplit)):
				mbName += mbSplit[idx]
			
			imapMgr = PyGMIMAPMgr("load-maillist",{"serverid": serverId, "mailbox": mbName})	
			imapMgr.setMainWindow(self)
			imapMgr.start()
		
	def addElemToMBTreeView(self,parent,el):
		self.mbTreeViewLock.acquire()
		treeIter = self._mailboxTreeView.get_model().append(parent,el)
		self.mbTreeViewLock.release()
		return treeIter
		
	"""
	Maillist Treeview
	"""
	
	def createMaillistTreeView(self):
		# TreeStore(Unread/Answered, Urgent, From, Subject, Date, Id, mailbox, serverId)
		maillistTreeStore = Gtk.TreeStore(str,int,str,str,str,str,str,str)

		self.mlTreeViewLock.acquire()
		self._maillistListView = self._builder.get_object("maillistTreeView")
		self._maillistListView.set_model(maillistTreeStore)

		# table columns (icons)
		renderer = Gtk.CellRendererPixbuf()
		mlCol = Gtk.TreeViewColumn("R", renderer, stock_id=0)
		mlCol.set_resizable(True)
		self._maillistListView.append_column(mlCol)
		# Table columns (text only)
		mlListViewCols = [("U",1),("De",2),("Objet",3),("Date",4)]
		
		for col in mlListViewCols:
			renderer = Gtk.CellRendererText()
			mlCol = Gtk.TreeViewColumn(col[0], renderer, text=col[1])
			mlCol.set_resizable(True)
			self._maillistListView.append_column(mlCol)
		
		# Event handler
		select = self._maillistListView.get_selection()
		select.connect("changed", self.onMaillistSelectionChanged)
		
		self.mlTreeViewLock.release()
	
	def onMaillistSelectionChanged(self,selection):
		model, treeiter = selection.get_selected()
		if model == None:
			return
			
		mailId = model[treeiter][5]
		mboxName = model[treeiter][6]
		serverId = model[treeiter][7]
		
		# we need an imapManager to get the mail
		imapMgr = PyGMIMAPMgr("load-mail",{"serverid": serverId, "mailbox": mboxName, "mailid": mailId})
		imapMgr.setMainWindow(self)
		imapMgr.start()
	
	def addElemToMLTreeView(self,parent,el):
		self.mbTreeViewLock.acquire()
		treeIter = self._maillistListView.get_model().append(parent,el)
		self.mbTreeViewLock.release()
		return treeIter
	
	def clearMLTreeView(self):
		self.mbTreeViewLock.acquire()
		self._maillistListView.get_model().clear()
		self.mbTreeViewLock.release()
		
	"""
	Mail view
	"""
		
	def createMailView(self):
		mailContainer = self._builder.get_object("mailviewContainer")
		self._mailTextView = GnomeHTMLTextView.HtmlTextView()
		self._mailTextView.set_left_margin(10)
		self._mailTextView.set_right_margin(10)
		mailContainer.add(self._mailTextView)
	
	def setMailViewText(self,_text,_html = False):
		self.mTextViewLock.acquire()
		if _html == False:
			mailbuffer = self._mailTextView.get_buffer()
			mailbuffer.set_text(_text)
		else:
			self._mailTextView.display_html(_text)
		self.mTextViewLock.release()
	"""
	Headerbar
	"""
	
	def createHeaderBar(self):
		self._headerBar = Gtk.HeaderBar()
		self._headerBar.props.show_close_button = True
		self._headerBar.props.title = PyGMailConfig.getAppNameAndVersion()
		self._window.set_titlebar(self._headerBar)
		
		# Send/Receive button
		srButton = Gtk.Button()
		srButton.connect("clicked", self.onSendReceiveButtonClicked)
		icon = Gio.ThemedIcon(name="mail-send-receive-symbolic")
		image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
		srButton.add(image)
		self._headerBar.pack_end(srButton)
		
	def onSendReceiveButtonClicked(self,button):
		imapThread = PyGMIMAPMgr("load-mailboxes")
		imapThread.setMainWindow(self)
		imapThread.start()
		
	# Window loading state
	def isWindowReady(self):
		self.readyLock.acquire()
		ready = self.isReady
		self.readyLock.release()
		return ready
