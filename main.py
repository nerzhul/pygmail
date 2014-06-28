#! /usr/bin/python2.7

from gi.repository import Gtk

from PyGMWindow import MainWindow
from PyGMConfig import PyGMailConfig
from PyGMSQL import PyGMSQLiteMgr
from PyGMIMAP import PyGMIMAPMgr

import logging

if __name__ == '__main__':
	# Init logger
	# Init logger
	logger = logging.getLogger("PyGMail")
	try:
		handler = logging.FileHandler("/var/log/pygmail.log")
		print "Logging to: /var/log/pygmail.log"
	except IOError:
		handler = logging.FileHandler("/tmp/pygmail.log")
		print "Logging to: /tmp/pygmail.log"
		
	formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler) 
	logger.setLevel(logging.INFO)
	
	# Init SQLMgr
	sqlMgr = PyGMSQLiteMgr()
	sqlMgr.Connect()
	
	imapThread = PyGMIMAPMgr()
	win = MainWindow(sqlMgr)
	
	imapThread.setMainWindow(win)
	imapThread.start()
	
	win.show_all()
	win.addThreadToKill(imapThread)
	Gtk.main()

