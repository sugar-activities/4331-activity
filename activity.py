# -*- coding: utf-8 -*-
# Copyright 2010, Peter Hewitt
# Copyright 2013, 14, Walter Bender
# Copyright 2013, Ignacio Rodriguez

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" This is a refactoring of Spirolaterals by Peter Hewitt. Peter's
version was based on the pygame library. This version uses Gtk and
Cairo. """

from gettext import gettext as _
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton, StopButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3 import profile

import Spirolaterals


def _luminance(color):
    ''' Calculate luminance value '''
    return int(color[1:3], 16) * 0.3 + int(color[3:5], 16) * 0.6 + \
        int(color[5:7], 16) * 0.1


def _lighter_color(colors):
    ''' Which color is lighter? Use that one for the text nick color '''
    if _luminance(colors[0]) > _luminance(colors[1]):
        return 0
    return 1


def is_low_contrast(colors):
    ''' We require lots of luminance contrast to make color text legible. '''
    # To turn off color on color, always return False
    return _luminance(colors[0]) - _luminance(colors[1]) < 96


class PeterActivity(activity.Activity):
    _LOWER = 0
    _UPPER = 1000

    def __init__(self, handle):
        super(PeterActivity, self).__init__(handle)

        # Get user's Sugar colors
        sugarcolors = profile.get_color().to_string().split(',')
        i = _lighter_color(sugarcolors)
        self.sugarcolors = [sugarcolors[i], sugarcolors[1 - i]]
        colors = [[int(self.sugarcolors[0][1:3], 16),
                   int(self.sugarcolors[0][3:5], 16),
                   int(self.sugarcolors[0][5:7], 16)],
                  [int(self.sugarcolors[1][1:3], 16),
                   int(self.sugarcolors[1][3:5], 16),
                   int(self.sugarcolors[1][5:7], 16)]]

        # Read any metadata from previous sessions
        if 'score' in self.metadata:
            score = int(self.metadata['score'])
        else:
            score = 0
        if 'level' in self.metadata:
            pattern = int(self.metadata['level'])
        else:
            pattern = 1
        if 'last' in self.metadata and self.metadata['last'] != 'None':
            last = int(self.metadata['last'])
        else:
            last = None
        if 'delay' in self.metadata:
            delay = int(self.metadata['delay'])
        else:
            delay = 500

        # No sharing
        self.max_participants = 1

        # Build the activity toolbar.
        toolbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self._separator0 = Gtk.SeparatorToolItem()
        self._separator0.props.draw = False
        if Gdk.Screen.width() > 1023:
            toolbox.toolbar.insert(self._separator0, -1)
        self._separator0.show()

        self._add_speed_slider(toolbox.toolbar, delay)

        self._separator1 = Gtk.SeparatorToolItem()
        self._separator1.props.draw = False
        if Gdk.Screen.width() > 1023:
            toolbox.toolbar.insert(self._separator1, -1)
        self._separator1.show()

        self.green = ToolButton('green')
        toolbox.toolbar.insert(self.green, -1)
        self.green.set_tooltip(_('Draw'))
        self.green.connect('clicked', self._button_cb, 'green')
        self.green.show()

        red = ToolButton('red')
        toolbox.toolbar.insert(red, -1)
        red.set_tooltip(_('Stop'))
        red.connect('clicked', self._button_cb, 'red')
        red.show()

        self.cyan = ToolButton('cyan')
        toolbox.toolbar.insert(self.cyan, -1)
        self.cyan.set_tooltip(_('Next pattern'))
        self.cyan.connect('clicked', self._button_cb, 'cyan')
        self.cyan.set_sensitive(False)
        self.cyan.show()

        self._separator2 = Gtk.SeparatorToolItem()
        self._separator2.props.draw = False
        if Gdk.Screen.width() > 1023:
            toolbox.toolbar.insert(self._separator2, -1)
        self._separator2.show()

        self._score_image = Gtk.Image()
        item = Gtk.ToolItem()
        item.add(self._score_image)
        toolbox.toolbar.insert(item, -1)
        item.show()

        self.separator3 = Gtk.SeparatorToolItem()
        self.separator3.props.draw = False
        self.separator3.set_expand(True)
        toolbox.toolbar.insert(self.separator3, -1)
        self.separator3.show()

        stop_button = StopButton(self)
        stop_button.props.accelerator = _('<Ctrl>Q')
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

        toolbox.show()
        self.set_toolbar_box(toolbox)

        self._toolbar = toolbox.toolbar

        # Create a canvas
        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(),
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._landscape = Gdk.Screen.width() > Gdk.Screen.height()

        self._game = Spirolaterals.Spirolaterals(
            canvas, colors, self, score=score, pattern=pattern, last=last,
            delay=delay)

        Gdk.Screen.get_default().connect('size-changed', self.__configure_cb)

    def __configure_cb(self, event):
        ''' Screen size/orientation has changed '''

        # We only redraw if orientation has changed.
        if self._landscape == Gdk.Screen.width() > Gdk.Screen.height():
            return

        if Gdk.Screen.width() < 1024 and \
                self._separator1 in self._toolbar:
            self._toolbar.remove(self._separator0)
            self._toolbar.remove(self._separator1)
            self._toolbar.remove(self._separator2)
            self.separator3.set_expand(False)
        elif self._separator1 not in self._toolbar:
            self._toolbar.insert(self._separator0, 1)
            self._toolbar.insert(self._separator1, 5)
            self._toolbar.insert(self._separator2, 9)
            self.separator3.set_expand(True)

        self._game.reset_level()

    def read_file(self, path):
        pass

    def write_file(self, path):
        self.metadata['score'] = str(self._game.score)
        self.metadata['level'] = str(self._game.pattern)
        self.metadata['last'] = str(self._game.last_pattern)
        self.metadata['delay'] = str(self._game.delay)

    def _button_cb(self, button=None, color=None):
        self._game.do_button(color)

    def _add_speed_slider(self, toolbar, delay):
        self._speed_stepper_down = ToolButton('speed-down')
        self._speed_stepper_down.set_tooltip(_('Slow down'))
        self._speed_stepper_down.connect('clicked',
                                         self._speed_stepper_down_cb)
        self._speed_stepper_down.show()

        self._adjustment = Gtk.Adjustment.new(
            delay, self._LOWER, self._UPPER, 25, 100, 0)
        self._adjustment.connect('value_changed', self._speed_change_cb)
        self._speed_range = Gtk.HScale.new(self._adjustment)
        self._speed_range.set_inverted(True)
        self._speed_range.set_draw_value(False)
        self._speed_range.set_size_request(120, 15)
        self._speed_range.show()

        self._speed_stepper_up = ToolButton('speed-up')
        self._speed_stepper_up.set_tooltip(_('Speed up'))
        self._speed_stepper_up.connect('clicked', self._speed_stepper_up_cb)
        self._speed_stepper_up.show()

        self._speed_range_tool = Gtk.ToolItem()
        self._speed_range_tool.add(self._speed_range)
        self._speed_range_tool.show()

        toolbar.insert(self._speed_stepper_down, -1)
        toolbar.insert(self._speed_range_tool, -1)
        toolbar.insert(self._speed_stepper_up, -1)
        return

    def _speed_stepper_down_cb(self, button=None):
        new_value = self._speed_range.get_value() + 25
        if new_value <= self._UPPER:
            self._speed_range.set_value(new_value)
        else:
            self._speed_range.set_value(self._UPPER)

    def _speed_stepper_up_cb(self, button=None):
        new_value = self._speed_range.get_value() - 25
        if new_value >= self._LOWER:
            self._speed_range.set_value(new_value)
        else:
            self._speed_range.set_value(self._LOWER)

    def _speed_change_cb(self, button=None):
        self._game.do_slider(int(self._adjustment.get_value()))
        return True

    def update_score(self, score):
        pixbuf = _svg_str_to_pixbuf(_score_icon(score))
        self._score_image.set_from_pixbuf(pixbuf)
        self._score_image.show()

    def good_job_pixbuf(self):
        return _svg_str_to_pixbuf(_good_job_icon(self.sugarcolors[0]))

    def try_again_pixbuf(self):
        return _svg_str_to_pixbuf(_try_again_icon(self.sugarcolors[0]))

    def background_pixbuf(self):
        size = max(Gdk.Screen.width(), Gdk.Screen.height())
        return _svg_str_to_pixbuf(_rect(size, size, 0, self.sugarcolors[1]))

    def turtle_pixbuf(self):
        return _svg_str_to_pixbuf(_turtle_icon(self.sugarcolors[0]))

    def splot_pixbuf(self):
        return _svg_str_to_pixbuf(_splot_icon(self.sugarcolors[0]))

    def box_pixbuf(self, size):
        return _svg_str_to_pixbuf(_rect(size, size, 10, '#000000'))

    def number_pixbuf(self, size, number, color):
        return _svg_str_to_pixbuf(_number(size, 4, number, color))


def _turtle_icon(color):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="55"\n' + \
        'height="55">\n' + \
        '<g>\n' + \
        '<path d="M 27.497 48.279 C 26.944 48.279 26.398 48.244 25.86 48.179 L 27.248 50.528 L 28.616 48.215 C 28.245 48.245 27.875 48.279 27.497 48.279 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '<g>\n' + \
        '<path d="M 40.16 11.726 C 37.996 11.726 36.202 13.281 35.817 15.333 C 37.676 16.678 39.274 18.448 40.492 20.541 C 42.777 20.369 44.586 18.48 44.586 16.151 C 44.586 13.707 42.604 11.726 40.16 11.726 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '<path d="M 40.713 39.887 C 39.489 42.119 37.853 44.018 35.916 45.443 C 36.437 47.307 38.129 48.682 40.16 48.682 C 42.603 48.682 44.586 46.702 44.586 44.258 C 44.586 42.003 42.893 40.162 40.713 39.887 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '<path d="M 14.273 39.871 C 12.02 40.077 10.249 41.95 10.249 44.258 C 10.249 46.701 12.229 48.682 14.673 48.682 C 16.737 48.682 18.457 47.262 18.945 45.35 C 17.062 43.934 15.47 42.061 14.273 39.871 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '<path d="M 19.026 15.437 C 18.683 13.334 16.872 11.726 14.673 11.726 C 12.229 11.726 10.249 13.707 10.249 16.15 C 10.249 18.532 12.135 20.46 14.494 20.556 C 15.68 18.513 17.226 16.772 19.026 15.437 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '</g>\n' + \
        '<path d="M 27.497 12.563 C 29.405 12.563 31.225 12.974 32.915 13.691 C 33.656 12.615 34.093 11.314 34.093 9.908 C 34.093 6.221 31.104 3.231 27.416 3.231 C 23.729 3.231 20.74 6.221 20.74 9.908 C 20.74 11.336 21.192 12.657 21.956 13.742 C 23.68 12.993 25.543 12.563 27.497 12.563 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '<g>\n' + \
        '<path d="M 43.102 30.421 C 43.102 35.1554 41.4568 39.7008 38.5314 43.0485 C 35.606 46.3963 31.6341 48.279 27.497 48.279 C 23.3599 48.279 19.388 46.3963 16.4626 43.0485 C 13.5372 39.7008 11.892 35.1554 11.892 30.421 C 11.892 20.6244 18.9364 12.563 27.497 12.563 C 36.0576 12.563 43.102 20.6244 43.102 30.421 Z " fill="#FFFFFF" stroke="%s" stroke-width="3.5"/>\n' % color + \
        '</g>\n' + \
        '<g>\n' + \
        '<path d="M 25.875 33.75 L 24.333 29.125 L 27.497 26.538 L 31.112 29.164 L 29.625 33.833 Z " fill="%s" stroke="none"/>\n' % color + \
        '<path d="M 27.501 41.551 C 23.533 41.391 21.958 39.542 21.958 39.542 L 25.528 35.379 L 29.993 35.547 L 33.125 39.667 C 33.125 39.667 30.235 41.661 27.501 41.551 Z " fill="%s" stroke="none"/>\n' % color + \
        '<path d="M 18.453 33.843 C 17.604 30.875 18.625 26.959 18.625 26.959 L 22.625 29.126 L 24.118 33.755 L 20.536 37.988 C 20.536 37.987 19.071 35.998 18.453 33.843 Z " fill="%s" stroke="none"/>\n' % color + \
        '<path d="M 19.458 25.125 C 19.458 25.125 19.958 23.167 22.497 21.303 C 24.734 19.66 26.962 19.583 26.962 19.583 L 26.925 24.564 L 23.404 27.314 L 19.458 25.125 Z " fill="%s" stroke="none"/>\n' % color + \
        '<path d="M 32.084 27.834 L 28.625 24.959 L 29 19.75 C 29 19.75 30.834 19.708 32.959 21.417 C 35.187 23.208 36.321 26.4 36.321 26.4 L 32.084 27.834 Z " fill="%s" stroke="none"/>\n' % color + \
        '<path d="M 31.292 34.042 L 32.605 29.578 L 36.792 28.042 C 36.792 28.042 37.469 30.705 36.75 33.709 C 36.21 35.965 34.666 38.07 34.666 38.07 L 31.292 34.042 Z " fill="%s" stroke="none"/>\n' % color + \
        '</g>\n' + \
        '</g>\n' + \
        '</svg>'


def _good_job_icon(color):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="900"\n' + \
        'height="150">\n' + \
        '<g\n' + \
        'transform="translate(-323.5,-408.12501)"\n' + \
        'style="stroke-width:3;stroke-miterlimit:4">\n' + \
        '<path\n' + \
        'd="m 325,470.5 197,1 0,68 -196.5,17 z"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:#ffffff;stroke-width:3;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none" />\n' % color + \
        '<path\n' + \
        'd="m 523.58046,470.41954 c -0.13908,-5.26214 5.74754,-7.07818 9.44636,-9 8.61617,-4.24453 9.85572,-8.02297 12.47318,-16.41954 1.76159,-5.65019 1.81398,-11.70163 3,-17.5 0.72099,-3.52486 0.49972,-7.50946 2.5,-10.5 2.05742,-3.07595 5.4789,-5.36144 9,-6.5 2.6959,-0.87173 5.8359,-0.96454 8.5,0 2.44792,0.88627 4.49712,2.87417 6,5 2.77016,3.91842 4.78743,10.31663 4.20977,15.08046 -1.40645,11.59866 -4.33199,20.55541 -6.91954,29.18295 2.63914,4.35385 1.09045,0.91477 19.37546,1.70977 4.12891,2.16337 7.61581,4.72782 6.59773,10.23659 1.52418,5.05477 -3.98096,6.45467 -3.15615,9.34387 5.05679,2.02909 10.82214,5.37105 9.94637,10.26819 0.76071,9.82042 -3.39004,8.29484 -5.5,11.67817 1.54287,3.42335 2.23857,5.25348 2.91954,9.15614 0.89173,5.11047 -2.53079,8.96195 -9.55364,11.05363 -1.03862,3.55186 1.99938,6.55092 2.55364,10.20977 0.64307,4.24511 -1.56067,7.6627 -4.47318,9.08046 -25.61313,0.54849 -33.0002,0.80747 -57.5,0 -2.385,-0.0786 -3.62433,0.62247 -6.20977,-2.02682 -1.45872,-1.49473 -2.77989,-1.80492 -2.79023,-3.44636 z"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:#ffffff;stroke-width:3;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none" />\n' % color + \
        '<rect\n' + \
        'width="45"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="571.5"\n' + \
        'y="461"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="57"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="566"\n' + \
        'y="483"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="54.5"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="566.5"\n' + \
        'y="502.5"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="40.5"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="574"\n' + \
        'y="523"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '</g>\n' + \
        '<text>\n' + \
        '<tspan\n' + \
        'x="315.5"\n' + \
        'y="97.874992"\n' + \
        'style="font-size:48px;text-align:start;text-anchor:start;fill:%s;fill-opacity:1;font-family:abc123">' % color + \
        _('Good job!') + \
        '</tspan>\n' + \
        '</text>\n' + \
        '</svg>\n'


def _splot_icon(color):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="55"\n' + \
        'height="55">\n' + \
        '<path\n' + \
        'd="m 1.0483663,28.89507 c -0.17933087,-1.451786 0.071469,-3.216875 1.1078744,-4.245508 1.0826579,-1.074536 2.9297644,-0.859617 4.4314968,-1.111919 1.5288645,-0.25686 3.1340018,-0.0077 4.6329285,-0.404334 1.249294,-0.330544 3.199616,-0.362457 3.525055,-1.617337 0.1573,-0.606544 -0.563049,-1.209961 -1.107875,-1.516253 -1.058094,-0.594844 -2.575834,0.305982 -3.62577,-0.30325 -0.459544,-0.266654 -0.9055779,-0.78133 -0.9064426,-1.314085 -0.00106,-0.654229 0.4776873,-1.450079 1.1078736,-1.617338 1.19031,-0.315921 2.154838,1.228811 3.323624,1.617338 0.68129,0.226472 1.414025,0.558722 2.115033,0.404333 0.282085,-0.06213 0.589599,-0.239718 0.70501,-0.505417 0.419354,-0.965435 0.122748,-2.222042 -0.402863,-3.133591 -0.528026,-0.915737 -1.9136,-1.718419 -2.517896,-1.920587 C 12.83212,13.024956 10.206512,10.056428 9.6092127,7.9707783 9.2187073,6.607212 9.1662375,4.9309452 9.9113603,3.7252697 10.260379,3.1605266 10.962454,2.7521277 11.62353,2.7144343 c 0.660226,-0.037645 1.404198,0.2868849 1.812885,0.8086683 0.695907,0.8884863 0.360756,2.2323574 0.604296,3.3357568 0.315244,1.4282759 0.573938,2.8842934 1.107873,4.2455096 0.363154,0.925825 0.681032,1.953866 1.410022,2.628171 0.431134,0.398793 1.104349,1.002944 1.611453,0.707585 0.817682,-0.476251 0.18791,-1.888445 0.302147,-2.830339 0.09008,-0.742657 0.100717,-1.8195043 0.302149,-2.2238382 C 18.975786,8.9816136 19.48033,7.6510471 19.37865,6.7577759 19.196296,5.1557811 16.9716,3.996739 17.263617,2.4111837 c 0.125208,-0.6798368 0.822552,-1.4452519 1.510738,-1.4151695 0.451236,0.019725 0.753088,0.5844512 0.906442,1.0108353 0.285197,0.7929558 -0.08393,1.6842205 -0.100716,2.5270886 -0.01208,0.60638 -0.126168,1.2263685 0,1.8195035 0.291793,1.3717671 1.317009,2.4957321 1.71217,3.8411754 0.249705,0.850196 -0.283107,2.069919 0.402863,2.628171 0.470103,0.382577 1.264709,0.156374 1.812885,-0.101084 0.623906,-0.293024 0.884919,-1.068794 1.410022,-1.516252 0.461364,-0.393147 0.905964,-0.987298 1.510737,-1.010835 0.961218,-0.03741 2.014317,1.516252 2.517897,1.415169 0.503579,-0.101084 0.974488,-0.419302 1.309305,-0.808668 0.334098,-0.388531 0.631282,-0.9026663 0.604295,-1.4151702 -0.05077,-0.9641068 -1.351299,-1.5634369 -1.410021,-2.5270884 -0.04871,-0.7994157 0.499989,-1.5346038 0.906443,-2.223838 0.462005,-0.7834365 1.208588,-2.0216706 1.712168,-2.1227542 0.503579,-0.1010835 2.015445,-0.5732121 2.719328,0 0.506183,0.4122136 0.406505,1.2663684 0.402863,1.9205873 -0.0051,0.9319297 -0.361828,1.8296447 -0.604295,2.7292555 -0.230109,0.8537554 -0.720018,1.6468406 -0.805727,2.5270884 -0.08546,0.8776886 -0.211615,1.9127626 0.302148,2.6281716 0.324932,0.452466 0.956486,0.667137 1.510737,0.707586 0.699158,0.05102 1.412495,-0.245725 2.014317,-0.606502 0.529887,-0.317653 0.781236,-0.993398 1.309306,-1.314085 0.481489,-0.2924 1.103927,-0.749462 1.611454,-0.505418 0.910814,0.437964 1.313994,1.838034 1.107875,2.830339 -0.106587,0.513131 -0.682087,0.808394 -1.107875,1.111919 -0.881402,0.62831 -2.085953,0.72573 -2.92076,1.41517 -0.518473,0.42819 -1.189961,0.943704 -1.20859,1.617335 -0.01679,0.607203 0.473545,1.22963 1.007158,1.516253 0.325595,0.174889 0.746124,0.07453 1.107874,0 0.751365,-0.154785 1.812885,-0.808667 2.115034,-0.909751 0.302147,-0.101084 4.230064,-2.830339 4.632928,-3.133589 0.402863,-0.303252 3.741504,-2.601621 5.841519,-2.426005 0.94687,0.07918 1.926174,0.699832 2.41718,1.516251 0.469701,0.780998 0.705273,1.969996 0.201432,2.729257 -0.353097,0.532096 -1.187396,0.485603 -1.812885,0.606501 -1.122788,0.217019 -2.920759,0.101083 -3.424339,0.202167 -0.503578,0.101084 -3.594384,0.103905 -5.136508,0.909752 -0.968573,0.506133 -2.007187,1.27382 -2.316464,2.324922 -0.136138,0.462678 0.106898,0.97433 0.302147,1.415169 0.302788,0.683639 1.186853,1.081528 1.309307,1.819503 0.132589,0.799067 -0.302148,2.122755 -0.705012,2.324921 -0.402863,0.202168 -1.309305,1.11192 -1.309305,1.718422 0,0.6065 0.868544,2.184103 1.812885,2.729254 1.428641,0.824729 3.363283,-0.194261 4.935076,0.30325 1.164132,0.368477 2.376426,0.950711 3.12219,1.920587 0.921396,1.198289 1.272655,2.83341 1.309307,4.346593 0.03364,1.38885 -0.0969,2.996724 -1.007159,4.043342 -0.475554,0.546792 -1.316704,0.999889 -2.014316,0.808669 -1.431587,-0.392407 -1.985607,-2.24327 -2.719328,-3.537925 -0.946259,-1.669681 -1.611454,-5.054177 -2.115033,-5.357427 -0.503578,-0.303252 -3.067806,-2.526401 -4.431497,-1.718421 -0.641909,0.380329 -0.389667,1.480874 -0.302147,2.223839 0.07613,0.646247 0.464331,1.215248 0.70501,1.819503 0.754432,1.894101 2.391585,3.622231 2.316465,5.660678 -0.04161,1.129376 -0.39924,2.851477 -1.510737,3.032506 -0.702973,0.114493 -1.510738,-1.111919 -1.510738,-1.516253 0,-0.404333 -0.04267,-4.141808 -1.309307,-5.559594 -0.737219,-0.825196 -2.052647,-1.387831 -3.12219,-1.111919 -0.391533,0.101004 -0.650692,0.535038 -0.805728,0.909752 -0.425652,1.028784 0.302149,2.931423 -0.201431,3.335756 -0.503578,0.404334 -1.739605,1.101337 -2.517895,0.707585 -0.673686,-0.340829 -0.521383,-1.421403 -0.805727,-2.122754 -0.413702,-1.02042 -0.705011,-2.830339 -1.309306,-3.032507 -0.604294,-0.202166 -1.512881,0.130686 -1.812885,0.707586 -0.527457,1.014287 0.705011,2.931423 0.805727,3.335757 0.100715,0.404333 0.805727,3.032505 1.107873,3.436839 0.302149,0.404335 3.46433,4.758446 2.517896,7.075848 -0.410027,1.00398 -1.96788,1.927721 -2.920759,1.41517 -0.866239,-0.465948 -0.261788,-1.955245 -0.402863,-2.931422 -0.224227,-1.551555 -0.367361,-3.119116 -0.705011,-4.649844 -0.310006,-1.405401 -0.906443,-3.234673 -1.20859,-4.144425 -0.302148,-0.909751 -1.20859,-4.85201 -1.913601,-4.953092 -0.705011,-0.101084 -1.252617,0.565741 -1.611453,1.111918 -0.282705,0.4303 -0.327597,1.00146 -0.302148,1.516252 0.06262,1.266807 1.017028,2.373926 1.107874,3.639008 0.06348,0.884071 0.201432,2.223838 -0.402863,2.628173 -0.604294,0.404334 -1.871137,0.957852 -2.517897,0.404334 -0.587545,-0.502842 -0.100714,-1.920588 0,-2.324921 0.100717,-0.404335 0.705012,-3.13359 0.604296,-3.537925 -0.100716,-0.404334 -0.211405,-3.734916 -1.611453,-3.942257 -0.68469,-0.1014 -0.979713,1.00653 -1.309306,1.617336 -0.889868,1.649111 -1.34525,3.518513 -1.712169,5.357428 -0.310954,1.558425 0,3.335756 -0.402863,4.750926 -0.402864,1.415169 -0.438749,3.374759 -1.208591,4.85201 -0.4962,0.952158 -1.117114,2.036782 -2.115033,2.426005 -0.566724,0.221042 -1.36131,0.206456 -1.812885,-0.202168 -0.586876,-0.531058 -0.622246,-1.540841 -0.503579,-2.324921 0.34769,-2.297348 2.406521,-3.977896 3.424339,-6.065012 0.959317,-1.967157 1.931001,-3.955566 2.517896,-6.065012 0.483965,-1.739495 1.208589,-5.155261 0.805726,-5.357428 -0.402863,-0.202168 -0.345745,-0.05736 -0.503579,0 -0.493088,0.179175 -0.759521,0.739027 -1.208589,1.010836 -0.52854,0.319908 -1.131671,0.918044 -1.712171,0.707583 -0.607357,-0.220196 -0.906442,-1.010834 -0.906442,-1.718419 0,-0.707586 0.240943,-2.71076 -0.705011,-3.335756 -0.42895,-0.28341 -1.071036,0.03695 -1.510737,0.303249 -0.592575,0.358884 -0.845778,1.101508 -1.3093065,1.617338 -1.0175297,1.132341 -1.7119039,3.075599 -3.2229069,3.234672 -0.7964462,0.08384 -1.7938557,-0.541402 -2.0143167,-1.314085 -0.1529858,-0.536192 0.2014317,-1.11192 0.7050108,-1.516253 0.5035793,-0.404334 3.8488659,-1.35626 5.1365083,-2.830339 0.427435,-0.489324 0.716033,-1.168849 0.705011,-1.819503 -0.01304,-0.769719 -0.158497,-1.952099 -0.906443,-2.122756 -0.6959909,-0.158802 -1.1499334,0.868722 -1.6114535,1.41517 -0.5361502,0.634812 -0.7303023,1.527063 -1.3093059,2.122755 -0.7282492,0.749238 -1.5979737,1.503335 -2.6186118,1.718419 -0.799409,0.168464 -1.7507382,0.06971 -2.4171801,-0.404334 C 1.5310386,30.472034 1.142646,29.658319 1.0483663,28.89507 z"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:none" />\n' % color + \
        '</svg>'


def _score_icon(score):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="55"\n' + \
        'height="55"\n' + \
        'viewBox="0 0 55 55">\n' + \
        '<path\n' + \
        'd="M 27.497,50.004 C 39.927,50.004 50,39.937 50,27.508 50,'\
        '15.076 39.927,4.997 27.497,4.997 15.071,4.997 5,15.076 5,27.508 '\
        '5,39.937 15.071,50.004 27.497,50.004 z"\n' + \
        'style="fill:#ffffff;fill-opacity:1" /><text\n' + \
        'style="fill:#000000;fill-opacity:1;stroke:none;font-family:Sans">'\
        '<tspan\n' + \
        'x="27.5"\n' + \
        'y="37.3"\n' + \
        'style="font-size:24px;text-align:center;text-anchor:middle;font-family:abc123">'\
        '%d' % score + \
        '</tspan></text>\n' + \
        '</svg>'


def _number(size, radius, number, color):
    if is_low_contrast([color, '#808080']):
        color = '#000000'

    x = size / 2.
    y = size * 4 / 5.
    pt = size * 0.96
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="%d"\n' % size + \
        'height="%d"\n' % size + \
        'viewBox="0 0 %d %d">\n' % (size, size) + \
        '<rect\n' + \
        'width="%d"\n' % size + \
        'height="%d"\n' % size + \
        'ry="%d"\n' % radius + \
        'x="0"\n' + \
        'y="0"\n' + \
        'style="fill:#808080;fill-opacity:1;stroke:none;" />\n' + \
        '<text>\n' + \
        '<tspan\n' + \
        'x="%f" ' % x + \
        'y="%f" ' % y + \
        'style="font-size:%fpx;' % pt + \
        'text-align:center;text-anchor:middle;' + \
        'fill:%s;font-family:abc123">' % color + \
        str(number) + \
        '</tspan></text>\n' + \
        '</svg>'


def _rect(height, width, radius, color):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="%d"\n' % width + \
        'height="%d"\n' % height + \
        'viewBox="0 0 %d %d">\n' % (width, height) + \
        '<rect\n' + \
        'width="%d"\n' % width + \
        'height="%d"\n' % height + \
        'ry="%d"\n' % radius + \
        'x="0"\n' + \
        'y="0"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:none;" />\n' % color + \
        '</svg>'


def _try_again_icon(color):
    return \
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
        '<svg\n' + \
        'xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
        'xmlns:cc="http://creativecommons.org/ns#"\n' + \
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
        'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
        'xmlns="http://www.w3.org/2000/svg"\n' + \
        'version="1.1"\n' + \
        'width="900"\n' + \
        'height="150">\n' + \
        '<g\n' + \
        'transform="matrix(1,0,0,-1,-323.5,558.18595)"\n' + \
        'style="stroke-width:3;stroke-miterlimit:4">\n' + \
        '<path\n' + \
        'd="m 325,470.5 197,1 0,68 -196.5,17 z"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:#ffffff;stroke-width:3;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none" />\n' % color + \
        '<path\n' + \
        'd="m 523.58046,470.41954 c -0.13908,-5.26214 5.74754,-7.07818 9.44636,-9 8.61617,-4.24453 9.85572,-8.02297 12.47318,-16.41954 1.76159,-5.65019 1.81398,-11.70163 3,-17.5 0.72099,-3.52486 0.49972,-7.50946 2.5,-10.5 2.05742,-3.07595 5.4789,-5.36144 9,-6.5 2.6959,-0.87173 5.8359,-0.96454 8.5,0 2.44792,0.88627 4.49712,2.87417 6,5 2.77016,3.91842 4.78743,10.31663 4.20977,15.08046 -1.40645,11.59866 -4.33199,20.55541 -6.91954,29.18295 2.63914,4.35385 1.09045,0.91477 19.37546,1.70977 4.12891,2.16337 7.61581,4.72782 6.59773,10.23659 1.52418,5.05477 -3.98096,6.45467 -3.15615,9.34387 5.05679,2.02909 10.82214,5.37105 9.94637,10.26819 0.76071,9.82042 -3.39004,8.29484 -5.5,11.67817 1.54287,3.42335 2.23857,5.25348 2.91954,9.15614 0.89173,5.11047 -2.53079,8.96195 -9.55364,11.05363 -1.03862,3.55186 1.99938,6.55092 2.55364,10.20977 0.64307,4.24511 -1.56067,7.6627 -4.47318,9.08046 -25.61313,0.54849 -33.0002,0.80747 -57.5,0 -2.385,-0.0786 -3.62433,0.62247 -6.20977,-2.02682 -1.45872,-1.49473 -2.77989,-1.80492 -2.79023,-3.44636 z"\n' + \
        'style="fill:%s;fill-opacity:1;stroke:#ffffff;stroke-width:3;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none" />\n' % color + \
        '<rect\n' + \
        'width="45"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="571.5"\n' + \
        'y="461"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="57"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="566"\n' + \
        'y="483"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="54.5"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="566.5"\n' + \
        'y="502.5"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '<rect\n' + \
        'width="40.5"\n' + \
        'height="20"\n' + \
        'ry="10"\n' + \
        'x="574"\n' + \
        'y="523"\n' + \
        'style="fill:%s;fill-opacity:1;fill-rule:nonzero;stroke:#ffffff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />\n' % color + \
        '</g>\n' + \
        '<text>\n' + \
        '<tspan\n' + \
        'x="315.5"\n' + \
        'y="97.874992"\n' + \
        'style="font-size:48px;text-align:start;text-anchor:start;fill:%s;fill-opacity:1;font-family:abc123">' % color + \
        _('Try again.') + \
        '</tspan>\n' + \
        '</text>\n' + \
        '</svg>'


def _svg_str_to_pixbuf(svg_string):
    ''' Load pixbuf from SVG string '''
    pl = GdkPixbuf.PixbufLoader.new_with_type('svg')
    pl.write(svg_string)
    pl.close()
    pixbuf = pl.get_pixbuf()
    return pixbuf
