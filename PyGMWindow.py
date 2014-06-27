#! /usr/bin/python2.7

from gi.repository import Gtk
from PyGMConfig import PyGMailConfig

class MainWindow(Gtk.Window):
	myGrid = None
	mainWrapper = None
	myHeaderBar = None
	_sqlMgr = None
	
	_toKillThreads = []
	
	def __init__(self,sqlMgr):
		Gtk.Window.__init__(self, title=PyGMailConfig.getAppNameAndVersion())
		
		_sqlMgr = sqlMgr

		# Window options
		self.set_border_width(10)
		self.set_default_size(800, 200)

		# First, create the header bar
		self.myHeaderBar = Gtk.HeaderBar()
		self.myHeaderBar.props.show_close_button = True
		self.myHeaderBar.props.title = PyGMailConfig.getAppNameAndVersion()
		self.set_titlebar(self.myHeaderBar)

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

		# Attach elements to grid
		self.myGrid.attach(self.label,1,2,2,2)

		# Events
		self.connect("delete-event", self.closeWindow)

		# Complete
		self.setFooterText("Initialization complete")

	def closeWindow(self,_window,_event):
		self.killAllRunningThreads()
		Gtk.main_quit()

	def setFooterText(self,_text):
		context = self.footerBar.get_context_id("example")
		self.footerBar.pop(context)
		self.footerBar.push(context, "%s" % _text)
	
	# We bufferize pointer to running threads
	def addThreadToKill(self,thread):
		if thread not in self._toKillThreads:
			self._toKillThreads +=  [thread,]

	# When main windows is closed, we need to kill all threads
	def killAllRunningThreads(self):
		for thread in self._toKillThreads:
			thread._Thread__stop()
		
