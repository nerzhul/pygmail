#! /usr/bin/python2.7

from gi.repository import Gtk

from PyGMWindow import MainWindow
from PyGMConfig import PyGMailConfig
from PyGMSQL import PyGMSQLiteMgr
from PyGMIMAP import PyGMIMAPMgr

if __name__ == '__main__':
	# Init SQLMgr
	sqlMgr = PyGMSQLiteMgr()
	print sqlMgr.Connect()
	
	imapMgr = PyGMIMAPMgr(sqlMgr)
	imapMgr.getIMAPServers()
	win = MainWindow(sqlMgr)
	win.show_all()
	Gtk.main()

