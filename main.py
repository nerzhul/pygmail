#! /usr/bin/python2.7

from gi.repository import Gtk

from PyGMWindow import MainWindow
from PyGMConfig import PyGMailConfig

if __name__ == '__main__':
	win = MainWindow()
	win.show_all()
	Gtk.main()

