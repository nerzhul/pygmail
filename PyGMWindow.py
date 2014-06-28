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

from gi.repository import Gtk
from PyGMConfig import PyGMailConfig
import threading

class MainWindow(Gtk.Window):
	# Interface stores
	myGrid = None
	mainWrapper = None
	_headerBar = None
	_mailboxTreeView = None
	mbTreeViewLock = threading.Lock()
	
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

		# Window options
		self.set_border_width(10)
		self.set_default_size(800, 400)

		# First, create the header bar
		self._headerBar = Gtk.HeaderBar()
		self._headerBar.props.show_close_button = True
		self._headerBar.props.title = PyGMailConfig.getAppNameAndVersion()
		self.set_titlebar(self._headerBar)

		# Create the main wrapper
		self.mainWrapper = Gtk.Grid()
		self.add(self.mainWrapper)

		# Now the component grid
		self.myGrid = Gtk.Grid()
		self.myGrid.set_border_width(10)
		self.footerBar = Gtk.Statusbar()
		self.footerBar.set_border_width(0);

		# Attach the components to the main Grid
		self.mainWrapper.attach(self.myGrid,0,1,1,1)
		self.mainWrapper.attach(self.footerBar,0,2,1,1)
		self.setFooterText("Initialization in progress...")

		self.label = Gtk.Label(label="Hello World", halign=Gtk.Align.END)
		
		# TreeStore(Label,LeafType,Value (serverId or real IMAP Path))
		mailboxTreeStore = Gtk.TreeStore(str,int,str)

		self.mbTreeViewLock.acquire()
		self._mailboxTreeView = Gtk.TreeView(mailboxTreeStore)
		renderer = Gtk.CellRendererText()
		self._mainTreeViewCol = Gtk.TreeViewColumn("Boîte de réception", renderer, text=0)
		self._mailboxTreeView.append_column(self._mainTreeViewCol)
		self.mbTreeViewLock.release()
		
		# Attach elements to grid
		mbtvScroll = Gtk.ScrolledWindow()
		mbtvScroll.add(self._mailboxTreeView)
		mbtvScroll.set_hexpand(True)
		mbtvScroll.set_vexpand(True)
		
		self.myGrid.attach(scrollWindow,1,0,1,1)

		# Events
		self.connect("delete-event", self.closeWindow)

		# Complete
		self.setFooterText("Initialization complete")
		
		self.readyLock.acquire()
		self.isReady = True
		self.readyLock.release()

	def setFooterText(self,_text):
		context = self.footerBar.get_context_id("PyGMail")
		self.footerBar.pop(context)
		self.footerBar.push(context, "%s" % _text)
		
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
		
	# Some get helpers
	def getMailboxGTKStore(self):
		self.mbTreeViewLock.acquire()
		model = self._mailboxTreeView.get_model()
		self.mbTreeViewLock.release()
		return model
		
	def addElemToMBTreeView(self,parent,el):
		self.mbTreeViewLock.acquire()
		treeIter = self._mailboxTreeView.get_model().append(parent,el)
		self.mbTreeViewLock.release()
		return treeIter
		
	def isWindowReady(self):
		self.readyLock.acquire()
		ready = self.isReady
		self.readyLock.release()
		return ready
