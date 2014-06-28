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
import threading, re

class MainWindow(Gtk.Window):
	# Interface stores
	myGrid = None
	mainWrapper = None
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
	
	def __init__(self,sqlMgr):
		Gtk.Window.__init__(self, title=PyGMailConfig.getAppNameAndVersion())
		
		_sqlMgr = sqlMgr
		
		# Init mutexes
		self.readyLock = threading.Lock()
		self.mbTreeViewLock = threading.Lock()
		self.mlTreeViewLock = threading.Lock()
		self.footerLock = threading.Lock()

		# Window options
		self.set_border_width(10)
		self.set_default_size(800, 400)

		# First, create the header bar
		self.createHeaderBar()

		# Create the main wrapper
		self.mainWrapper = Gtk.Grid()
		self.add(self.mainWrapper)

		# Now the component grid
		self.myGrid = Gtk.Grid()
		self.myGrid.set_border_width(10)
		self._footerBar = Gtk.Statusbar()
		self._footerBar.set_border_width(0);

		# Attach the components to the main Grid
		self.mainWrapper.attach(self.myGrid,0,1,1,1)
		self.mainWrapper.attach(self._footerBar,0,2,1,1)
		self.setFooterText("Initialization in progress...")

		self.createMailboxTreeView()
		self.createMaillistTreeView()
		self.createMailView()

		# Events
		self.connect("delete-event", self.closeWindow)

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
		self._mailboxTreeView = Gtk.TreeView(mailboxTreeStore)
		
		# Table columns
		renderer = Gtk.CellRendererText()
		mbTreeViewCol = Gtk.TreeViewColumn("Boîte de réception", renderer, text=0)
		self._mailboxTreeView.append_column(mbTreeViewCol)
		
		# Event handler
		select = self._mailboxTreeView.get_selection()
		select.connect("changed", self.onMailboxSelectionChanged)
		
		self.mbTreeViewLock.release()
		
		# Attach elements to grid
		mbtvScroll = Gtk.ScrolledWindow()
		mbtvScroll.add(self._mailboxTreeView)
		mbtvScroll.set_hexpand(True)
		mbtvScroll.set_vexpand(True)
		
		self.myGrid.attach(mbtvScroll,1,0,1,1)

	def onMailboxSelectionChanged(self,selection):
		model, treeiter = selection.get_selected()
		mbSplit = re.split("-",model[treeiter][2])
		
		if len(mbSplit) >= 2:
			serverId = mbSplit[0]
			mbName = ""
			for idx in range(1,len(mbSplit)):
				mbName += mbSplit[idx]
			
			imapMgr = PyGMIMAPMgr()	
			imapMgr.setMainWindow(self)
			imapMgr.loadMailboxMails(serverId,mbName)
		
	def addElemToMBTreeView(self,parent,el):
		self.mbTreeViewLock.acquire()
		treeIter = self._mailboxTreeView.get_model().append(parent,el)
		self.mbTreeViewLock.release()
		return treeIter
		
	"""
	Maillist Treeview
	"""
	
	def createMaillistTreeView(self):
		# TreeStore(Label,LeafType,Value (serverId or real IMAP Path))
		maillistTreeStore = Gtk.TreeStore(int,int,str,str,str)

		self.mlTreeViewLock.acquire()
		self._maillistListView = Gtk.TreeView(maillistTreeStore)

		# Table columns
		rendererRead = Gtk.CellRendererText()
		mlListViewColRead = Gtk.TreeViewColumn("R", rendererRead, text=0)
		self._maillistListView.append_column(mlListViewColRead)
		
		rendererUrgent = Gtk.CellRendererText()
		mlListViewColUrgent = Gtk.TreeViewColumn("U", rendererUrgent, text=1)
		self._maillistListView.append_column(mlListViewColUrgent)
		
		rendererFrom = Gtk.CellRendererText()
		mlListViewColFrom = Gtk.TreeViewColumn("De", rendererFrom, text=2)
		self._maillistListView.append_column(mlListViewColFrom)
		
		rendererSubject = Gtk.CellRendererText()
		mlListViewColSubject = Gtk.TreeViewColumn("Objet", rendererSubject, text=3)
		self._maillistListView.append_column(mlListViewColSubject)
		
		renderedDate = Gtk.CellRendererText()
		mlListViewColDate = Gtk.TreeViewColumn("Date", renderedDate, text=4)
		self._maillistListView.append_column(mlListViewColDate)
		
		# Event handler
		select = self._maillistListView.get_selection()
		select.connect("changed", self.onMaillistSelectionChanged)
		
		self.mlTreeViewLock.release()
		
		# Attach elements to grid
		mltvScroll = Gtk.ScrolledWindow()
		mltvScroll.add(self._maillistListView)
		mltvScroll.set_hexpand(True)
		mltvScroll.set_vexpand(True)
		
		self.myGrid.attach(mltvScroll,2,0,1,1)
	
	def onMaillistSelectionChanged(self,selection):
		model, treeiter = selection.get_selected()
		print model
	
	def addElemToMLTreeView(self,parent,el):
		self.mbTreeViewLock.acquire()
		treeIter = self._maillistListView.get_model().append(parent,el)
		self.mbTreeViewLock.release()
		return treeIter
		
	def createMailView(self):
		mailScroll = Gtk.ScrolledWindow()
		mailScroll.set_hexpand(True)
		mailScroll.set_vexpand(True)
	
		self._mailTextView = Gtk.TextView()
		textbuffer = self._mailTextView.get_buffer()
		textbuffer.set_text("This is some text inside of a Gtk.TextView. "
			+ "Select text and click one of the buttons 'bold', 'italic', "
			+ "or 'underline' to modify the text accordingly.")
		mailScroll.add(self._mailTextView)
		self.myGrid.attach(mailScroll,2,1,1,1)
		
	"""
	Headerbar
	"""
	
	def createHeaderBar(self):
		self._headerBar = Gtk.HeaderBar()
		self._headerBar.props.show_close_button = True
		self._headerBar.props.title = PyGMailConfig.getAppNameAndVersion()
		self.set_titlebar(self._headerBar)
		
		# Send/Receive button
		srButton = Gtk.Button()
		srButton.connect("clicked", self.onSendReceiveButtonClicked)
		icon = Gio.ThemedIcon(name="mail-send-receive-symbolic")
		image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
		srButton.add(image)
		self._headerBar.pack_end(srButton)
		
	def onSendReceiveButtonClicked(self,button):
		imapThread = PyGMIMAPMgr()
		imapThread.setMainWindow(self)
		imapThread.start()
		
	# Window loading state
	def isWindowReady(self):
		self.readyLock.acquire()
		ready = self.isReady
		self.readyLock.release()
		return ready
