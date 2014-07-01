# -*- coding: utf-8 -*-

### Copyright (C) 2005-2007 Gustavo J. A. M. Carneiro
### Copyright (C) 2014 Loic Blot
###
### This library is free software; you can redistribute it and/or
### modify it under the terms of the GNU Lesser General Public
### License as published by the Free Software Foundation; either
### version 2 of the License, or (at your option) any later version.
###
### This library is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
### Lesser General Public License for more details.
###
### You should have received a copy of the GNU Lesser General Public
### License along with this library; if not, write to the
### Free Software Foundation, Inc., 59 Temple Place - Suite 330,
### Boston, MA 02111-1307, USA.

'''
A gtk.TextView-based renderer for XHTML-IM, as described in:
  http://www.jabber.org/jeps/jep-0071.html
'''

import gobject
import pango
from gi.repository import Gdk
from gi.repository import Gtk
import xml.sax, xml.sax.handler
from xml.sax.handler import ErrorHandler
import HTMLParser
import re
import warnings
from cStringIO import StringIO
import urllib2
import operator

whitespace_rx = re.compile("\\s+")
allwhitespace_rx = re.compile("^\\s*$")

## pixels = points * display_resolution
"""
display_resolution = 0.3514598*(Gdk.screen_height() /
                    float(Gdk.screen_height_mm()))
"""
def _parse_css_color(color):
    '''_parse_css_color(css_color) -> Gdk.Color'''
    if color.startswith("rgb(") and color.endswith(')'):
        r, g, b = [int(c)*257 for c in color[4:-1].split(',')]
        return Gdk.Color(r, g, b)
    else:
        return Gdk.color_parse(color)

class HtmlHandler(xml.sax.handler.ContentHandler):
    
    def __init__(self, textview, startiter):
        xml.sax.handler.ContentHandler.__init__(self)
        self.textbuf = textview.get_buffer()
        self.textview = textview
        self.iter = startiter
        self.text = ''
        self.styles = [] # a gtk.TextTag or None, for each span level
        self.list_counters = [] # stack (top at head) of list
                                # counters, or None for unordered list

    def _parse_style_color(self, tag, value):
        color = _parse_css_color(value)
        tag.set_property("foreground-gdk", color)

    def _parse_style_background_color(self, tag, value):
        color = _parse_css_color(value)
        tag.set_property("background-gdk", color)
        tag.set_property("paragraph-background-gdk", color)


    if gobject.pygtk_version >= (2, 8, 1):

        def _get_current_attributes(self):
            attrs = self.textview.get_default_attributes()
            self.iter.backward_char()
            self.iter.get_attributes(attrs)
            self.iter.forward_char()
            return attrs
        
    else:
        
        ## Workaround http://bugzilla.gnome.org/show_bug.cgi?id=317455
        def _get_current_style_attr(self, propname, comb_oper=None):
            tags = [tag for tag in self.styles if tag is not None]
            tags.reverse()
            is_set_name = propname + "-set"
            value = None
            for tag in tags:
                if tag.get_property(is_set_name):
                    if value is None:
                        value = tag.get_property(propname)
                        if comb_oper is None:
                            return value
                    else:
                        value = comb_oper(value, tag.get_property(propname))
            return value

        class _FakeAttrs(object):
            __slots__ = ("font", "font_scale")

        def _get_current_attributes(self):
            attrs = self._FakeAttrs()
            attrs.font_scale = self._get_current_style_attr("scale",
                                                            operator.mul)
            if attrs.font_scale is None:
                attrs.font_scale = 1.0
            attrs.font = self._get_current_style_attr("font-desc")
            if attrs.font is None:
                attrs.font = self.textview.style.font_desc
            return attrs


    def __parse_length_frac_size_allocate(self, textview, allocation,
                                          frac, callback, args):
        callback(allocation.width*frac, *args)

    def _parse_length(self, value, font_relative, callback, *args):
        '''Parse/calc length, converting to pixels, calls callback(length, *args)
        when the length is first computed or changes'''
        if value.endswith('%'):
            frac = float(value[:-1])/100
            if font_relative:
                attrs = self._get_current_attributes()
                font_size = attrs.font.get_size() / pango.SCALE
                callback(frac*display_resolution*font_size, *args)
            else:
                ## CSS says "Percentage values: refer to width of the closest
                ##           block-level ancestor"
                ## This is difficult/impossible to implement, so we use
                ## textview width instead; a reasonable approximation..
                alloc = self.textview.get_allocation()
                self.__parse_length_frac_size_allocate(self.textview, alloc,
                                                       frac, callback, args)
                self.textview.connect("size-allocate",
                                      self.__parse_length_frac_size_allocate,
                                      frac, callback, args)

        elif value.endswith('pt'): # points
            callback(float(value[:-2])*display_resolution, *args)

        elif value.endswith('em'): # ems, the height of the element's font
            attrs = self._get_current_attributes()
            font_size = attrs.font.get_size() / pango.SCALE
            callback(float(value[:-2])*display_resolution*font_size, *args)

        elif value.endswith('ex'): # x-height, ~ the height of the letter 'x'
            ## FIXME: figure out how to calculate this correctly
            ##        for now 'em' size is used as approximation
            attrs = self._get_current_attributes()
            font_size = attrs.font.get_size() / pango.SCALE
            callback(float(value[:-2])*display_resolution*font_size, *args)

        elif value.endswith('px'): # pixels
            callback(int(value[:-2]), *args)

        else:
            warnings.warn("Unable to parse length value '%s'" % value)
        
    def __parse_font_size_cb(length, tag):
        tag.set_property("size-points", length/display_resolution)
    __parse_font_size_cb = staticmethod(__parse_font_size_cb)

    def _parse_style_font_size(self, tag, value):
        try:
            scale = {
                "xx-small": pango.SCALE_XX_SMALL,
                "x-small": pango.SCALE_X_SMALL,
                "small": pango.SCALE_SMALL,
                "medium": pango.SCALE_MEDIUM,
                "large": pango.SCALE_LARGE,
                "x-large": pango.SCALE_X_LARGE,
                "xx-large": pango.SCALE_XX_LARGE,
                } [value]
        except KeyError:
            pass
        else:
            attrs = self._get_current_attributes()
            tag.set_property("scale", scale / attrs.font_scale)
            return
        if value == 'smaller':
            tag.set_property("scale", pango.SCALE_SMALL)
            return
        if value == 'larger':
            tag.set_property("scale", pango.SCALE_LARGE)
            return
        self._parse_length(value, True, self.__parse_font_size_cb, tag)

    def _parse_style_font_style(self, tag, value):
        try:
            style = {
                "normal": pango.STYLE_NORMAL,
                "italic": pango.STYLE_ITALIC,
                "oblique": pango.STYLE_OBLIQUE,
                } [value]
        except KeyError:
            warnings.warn("unknown font-style %s" % value)
        else:
            tag.set_property("style", style)

    def __frac_length_tag_cb(length, tag, propname):
        tag.set_property(propname, length)
    __frac_length_tag_cb = staticmethod(__frac_length_tag_cb)
        
    def _parse_style_margin_left(self, tag, value):
        self._parse_length(value, False, self.__frac_length_tag_cb,
                           tag, "left-margin")

    def _parse_style_margin_right(self, tag, value):
        self._parse_length(value, False, self.__frac_length_tag_cb,
                           tag, "right-margin")

    def _parse_style_font_weight(self, tag, value):
        ## TODO: missing 'bolder' and 'lighter'
        try:
            weight = {
                '100': pango.WEIGHT_ULTRALIGHT,
                '200': pango.WEIGHT_ULTRALIGHT,
                '300': pango.WEIGHT_LIGHT,
                '400': pango.WEIGHT_NORMAL,
                '500': pango.WEIGHT_NORMAL,
                '600': pango.WEIGHT_BOLD,
                '700': pango.WEIGHT_BOLD,
                '800': pango.WEIGHT_ULTRABOLD,
                '900': pango.WEIGHT_HEAVY,
                'normal': pango.WEIGHT_NORMAL,
                'bold': pango.WEIGHT_BOLD,
                } [value]
        except KeyError:
            warnings.warn("unknown font-style %s" % value)
        else:
            tag.set_property("weight", weight)
        
    def characters(self, content):
        if allwhitespace_rx.match(content) is not None:
            return
        #if self.text:
        #    self.text += ' '
        self.text += whitespace_rx.sub(' ', content)

    def startElement(self, name, attrs):

        if name == 'div':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'span':
            pass
        elif name == 'img':
            try:
                ## Max image size = 10 MB (to try to prevent DoS)
                mem = urllib2.urlopen(attrs['src']).read(10*1024*1024)
                ## Caveat: GdkPixbuf is known not to be safe to load
                ## images from network... this program is now potentially
                ## hackable ;)
                loader = Gdk.PixbufLoader()
                loader.write(mem); loader.close()
                pixbuf = loader.get_pixbuf()
            except Exception, ex:
                pixbuf = None
                try:
                    alt = attrs['alt']
                except KeyError:
                    alt = "Broken image"
            if pixbuf is not None:
                tags = self._get_style_tags()
                if tags:
                    tmpmark = self.textbuf.create_mark(None, self.iter, True)

                self.textbuf.insert_pixbuf(self.iter, pixbuf)

                if tags:
                    start = self.textbuf.get_iter_at_mark(tmpmark)
                    for tag in tags:
                        self.textbuf.apply_tag(tag, start, self.iter)
                    self.textbuf.delete_mark(tmpmark)
            else:
                self._insert_text("[IMG: %s]" % alt)
        elif name == 'body':
            pass
        elif name == 'a':
            pass
        else:
            warnings.warn("Unhandled element '%s'" % name)

    def endElement(self, name):
        self._flush_text()
        if name == 'div':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'span':
            pass
        elif name == 'img':
            pass
        elif name == 'body':
            pass
        else:
            warnings.warn("Unhandled element '%s'" % name)
        self._end_span()
        
class HtmlTextView(Gtk.TextView):
    __gtype_name__ = 'HtmlTextView'
    __gsignals__ = {
        'url-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str)), # href, type
    }
    
    window = None
    
    def __init__(self):
		Gtk.TextView.__init__(self)
		self.set_wrap_mode(Gtk.WrapMode.CHAR)
		self.set_editable(False)
		self._changed_cursor = False
		self.connect("motion-notify-event", self.__motion_notify_event)
		self.connect("leave-notify-event", self.__leave_event)
		self.connect("enter-notify-event", self.__motion_notify_event)
		self.set_pixels_above_lines(3)
		self.set_pixels_below_lines(3)

    def __leave_event(self, widget, event):
        if self._changed_cursor:
            self.window = widget.get_window(Gtk.TEXT_WINDOW_TEXT)
            self.window.set_cursor(Gdk.Cursor(Gdk.XTERM))
            self._changed_cursor = False
    
    def __motion_notify_event(self, widget, event):
        """
        x, y, _ = widget.window.get_pointer()
        x, y = widget.window_to_buffer_coords(Gtk.TEXT_WINDOW_TEXT, x, y)
        tags = widget.get_iter_at_location(x, y).get_tags()
        for tag in tags:
            if getattr(tag, 'is_anchor', False):
                is_over_anchor = True
                break
        else:
            is_over_anchor = False
        if not self._changed_cursor and is_over_anchor:
            window = widget.get_window(Gtk.TEXT_WINDOW_TEXT)
            window.set_cursor(Gdk.Cursor(Gdk.HAND2))
            self._changed_cursor = True
        elif self._changed_cursor and not is_over_anchor:
            window = widget.get_window(Gtk.TEXT_WINDOW_TEXT)
            window.set_cursor(Gdk.Cursor(Gdk.XTERM))
            self._changed_cursor = False
         """
        return False

    def display_html(self, html):
		buffer = self.get_buffer()
		buffer.set_text("")
		eob = buffer.get_start_iter()
		parser = xml.sax.make_parser()
		parser.setContentHandler(HtmlHandler(self, eob))
		html = HTMLParser.HTMLParser().unescape(html)
		html = MyHTMLParser(self,eob).feed(html)
		print html
		#parser.parse(StringIO("<body>%s</body>" % html))

		if not eob.starts_line():
			buffer.insert(eob, "\n")

class MyHTMLParser(HTMLParser.HTMLParser):
	_textView = None
	_textBuffer = None
	_iter = None
	_styles = []
	_text = ""
	_prevTag = ""
	
	def __init__(self,tv,startiter):
		HTMLParser.HTMLParser.__init__(self)
		self._textView = tv
		self._textBuffer = tv.get_buffer()
		self._iter = startiter
		self._styles = []
		self.list_counters = [] # stack (top at head) of list
								# counters, or None for unordered list
	
	## build a dictionary mapping styles to methods, for greater speed
	__style_methods = dict()
	for style in ["background-color", "color", "font-family", "font-size",
			"font-style", "font-weight", "margin-left", "margin-right",
			"text-align", "text-decoration"]:
		try:
			method = locals()["_parse_style_%s" % style.replace('-', '_')]
		except KeyError:
			warnings.warn("Style attribute '%s' not yet implemented" % style)
		else:
			__style_methods[style] = method
	
	def _parse_style_font_family(self, tag, value):
		tag.set_property("family", value)

	def _parse_style_text_align(self, tag, value):
		try:
			align = {
				'left': Gtk.Justification.LEFT,
				'right': Gtk.Justification.RIGHT,
				'center': Gtk.Justification.CENTER,
				'justify': Gtk.Justification.FILL,
			} [value]
		except KeyError:
			warnings.warn("Invalid text-align:%s requested" % value)
		else:
			tag.set_property("justification", align)
    
	def _parse_style_text_decoration(self, tag, value):
		if value == "none":
			tag.set_property("underline", pango.UNDERLINE_NONE)
			tag.set_property("strikethrough", False)
		elif value == "underline":
			tag.set_property("underline", pango.UNDERLINE_SINGLE)
			tag.set_property("strikethrough", False)
		elif value == "overline":
			warnings.warn("text-decoration:overline not implemented")
			tag.set_property("underline", pango.UNDERLINE_NONE)
			tag.set_property("strikethrough", False)
		elif value == "line-through":
			tag.set_property("underline", pango.UNDERLINE_NONE)
			tag.set_property("strikethrough", True)
		elif value == "blink":
			warnings.warn("text-decoration:blink not implemented")
		else:
			warnings.warn("text-decoration:%s not implemented" % value)

	def _get_style_tags(self):
		return [tag for tag in self._styles if tag is not None]
		
	def _insert_text(self, text):
		tags = self._get_style_tags()
		if tags:
			self._textBuffer.insert_with_tags(self._iter, text, *tags)
		else:
			self._textBuffer.insert(self._iter, text)
	
	def _flush_text(self):
		if not self._text:
			return
		self._insert_text(self._text.replace('\n', ''))
		self._text = ''
		
	def handle_starttag(self, tag, attrs):
		self._flush_text()

		style = self._find_attr_val(attrs,"style")
		for attr in attrs:
			print "     attr:", attr

		tbtag = None
		if tag == 'a':
			tbtag = self._textBuffer.create_tag()
			tbtag.set_property('foreground', '#0000ff')
			tbtag.set_property('underline', pango.UNDERLINE_SINGLE)
			
			type_ = self._find_attr_val(attrs,"type")
			tbtag.connect('event', self._anchor_event, self._find_attr_val(attrs,"href"), type_)
			tbtag.is_anchor = True
			
		self._begin_span(style, tbtag)
		
		if tag == 'p':
			if not self._iter.starts_line():
				self._insert_text("\n")
		elif tag == 'br':
			pass # handled in handle_endtag
		elif tag == 'ul':
			if not self._iter.starts_line():
				self._insert_text("\n")
			self.list_counters.insert(0, None)
		elif tag == 'ol':
			if not self._iter.starts_line():
				self._insert_text("\n")
			self.list_counters.insert(0, 0)
		elif tag == 'li':
			if self.list_counters[0] is None:
				li_head = unichr(0x2022)
			else:
				self.list_counters[0] += 1
				li_head = "%i." % self.list_counters[0]
			self._text = ' '*len(self.list_counters)*4 + li_head + ' '
		elif tag == 'a':
			pass
		else:
			print "Start tag:", tag
	
	def handle_endtag(self, tag):
		self._flush_text()
		if tag == 'p':
			if not self._iter.starts_line():
				self._insert_text("\n")
		elif tag == 'br':
			if not self._iter.starts_line():
				self._insert_text("\n")
		elif tag == 'ul':
			self.list_counters.pop()
		elif tag == 'ol':
			self.list_counters.pop()
		elif tag == 'li':
			self._insert_text("\n")
		elif tag == 'a':
			pass
		else:
			print "End tag  :", tag
		
		self._end_span()
		
	def handle_data(self, data):
		self._insert_text(data)
		
	def handle_comment(self, data):
		print "Comment  :", data
		
	def handle_entityref(self, name):
		c = unichr(name2codepoint[name])
		print "Named ent:", c
		
	def handle_charref(self, name):
		if name.startswith('x'):
			c = unichr(int(name[1:], 16))
		else:
			c = unichr(int(name))
		print "Num ent  :", c
		
	def handle_decl(self, data):
		print "Decl     :", data
	
	def _anchor_event(self, tag, textview, event, iter, href, type_):
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			self._textView.emit("url-clicked", href, type_)
			return True
		return False
	
	def _begin_span(self, style, tag=None):
		if style is None:
			self._styles.append(tag)
			return None
		if tag is None:
			tag = self._textBuffer.create_tag()
		for attr, val in [item.split(':', 1) for item in style.split(';')]:
			attr = attr.strip().lower()
			val = val.strip()
			try:
				method = self.__style_methods[attr]
			except KeyError:
				warnings.warn("Style attribute '%s' requested "
							"but not yet implemented" % attr)
			else:
				method(self, tag, val)
		self._styles.append(tag)

	def _end_span(self):
		if len(self._styles) > 0:
			self._styles.pop(-1)

	def _find_attr_id(self,attrs,name):
		attrsLen = len(attrs)
		for i in range(0,attrsLen):
			if attrs[i] == name:
				return i
		
		return -1

	def _find_attr_val(self,attrs,name):
		typeId = self._find_attr_id(attrs,"type")
		if typeId != -1 and typeId+1 < len(attrs):
			return attrs[typeId+1]
		else:
			return None
