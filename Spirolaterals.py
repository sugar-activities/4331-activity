#!/usr/bin/python
# Spirolaterals.py
"""
    Copyright (C) 2014  Walter Bender
    Copyright (C) 2010  Peter Hewitt

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This is a refactoring of Peter's Spirolaterals game. It uses cairo
    and Gtk instead of pygame.

"""
import os
import cairo
import logging

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import PangoCairo

from sugar3.graphics import style

from sprites import Sprites, Sprite

# artwork positions/scale in [landscape, portrait]
BS = [400, 400]  # box scale
X1 = [25, 25]  # left/top box position
Y1 = [25, 25]
X2 = [475, 25]  # right/bottom box position
Y2 = [25, 475]
NX = [475, 475]  # number cards position
NY = [475, 475]
NS = [75, 75]  # number cards size
NO = [7, 7]  # offset between number cards
TX = [200, 225]  # target turtle position
TY = [350, 350]
TS = [50, 50]  # target turtle line length
UX = [650, 225]  # user turtle position
UY = [350, 775]
US = [50, 50]  # user turtle line length
GY = [500, 950]  # position of success/failure graphics
LS = [24, 24]  # font size for level indicator

NUMBER_LAYER = 10
TURTLE_LAYER = 6
SUCCESS_LAYER = 5
HIDDEN_LAYER = 0


class Spirolaterals:

    def __init__(self, canvas, colors, parent, score=0, delay=500, pattern=1,
                 last=None):
        self._canvas = canvas
        self._colors = colors
        self._parent = parent
        self.delay = delay
        self.score = score
        self.pattern = pattern
        self.last_pattern = last
        self._running = False

        self._turtle_canvas = None
        self._user_numbers = [1, 1, 1, 3, 2]
        self._active_index = 0

        self._sprites = Sprites(self._canvas)
        self._sprites.set_delay(True)

        size = max(Gdk.Screen.width(), Gdk.Screen.height())

        cr = self._canvas.get_property('window').cairo_create()
        self._turtle_canvas = cr.get_target().create_similar(
            cairo.CONTENT_COLOR, size, size)
        self._canvas.connect('draw', self.__draw_cb)

        self._cr = cairo.Context(self._turtle_canvas)
        self._cr.set_line_cap(1)  # Set the line cap to be round
        self._sprites.set_cairo_context(self._cr)

        self._canvas.set_can_focus(True)
        self._canvas.grab_focus()

        self._canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self._canvas.connect('button-press-event', self._button_press_cb)
        self._canvas.connect('key_press_event', self._keypress_cb)

        self._width = Gdk.Screen.width()
        self._height = Gdk.Screen.height() - style.GRID_CELL_SIZE

        if self._width < self._height:
            self.i = 1
        else:
            self.i = 0

        self._calculate_scale_and_offset()

        self._numbers = []
        self._glownumbers = []
        self._create_number_sprites()
        self._create_turtle_sprites()
        self._create_results_sprites()

        self._set_color(colors[0])
        self._set_pen_size(4)

        self.reset_level()

    def _calculate_scale_and_offset(self):
        self.offset = 0
        if self.i == 0:
            self.scale = self._height / (900. - style.GRID_CELL_SIZE) * 1.25
            self.offset = (self._width -
                           (self.sx(X1[self.i] + X2[self.i]) +
                            self.ss(BS[self.i]))) / 2.
        else:
            self.scale = self._width / 900.
            self.offset = (self._width -
                           (self.sx(X1[self.i]) +
                            self.ss(BS[self.i]))) / 2.

    def reset_level(self):
        self._width = Gdk.Screen.width()
        self._height = Gdk.Screen.height() - style.GRID_CELL_SIZE
        if self._width < self._height:
            self.i = 1
        else:
            self.i = 0

        self._calculate_scale_and_offset()

        self._show_background_graphics()
        self._show_user_numbers()

        self._get_goal()
        self._draw_goal()

        self._reset_sprites()

        if self.score > 0:
            self._parent.update_score(int(self.score))

    def _reset_sprites(self):
        x = self.sx(TX[self.i] - TS[self.i] / 2)
        y = self.sy(TY[self.i])
        self._target_turtle.move((x, y))

        x = self.sx(UX[self.i] - US[self.i] / 2)
        y = self.sy(UY[self.i])
        self._user_turtles[0].move((x, y))

        for i in range(5):
            for j in range(5):
                if self.i == 0:
                    x = self.sx(NX[self.i]) + i * (self.ss(NS[self.i]
                                                           + NO[self.i]))
                    y = self.sy(NY[self.i])
                else:
                    x = self.sx(NX[self.i])
                    y = self.sy(NY[self.i]) + i * (self.ss(NS[self.i]
                                                           + NO[self.i]))
                self._numbers[i][j].move((x, y))
                self._glownumbers[i][j].move((x, y))

        x = 0
        y = self.sy(GY[self.i])
        self._success.move((x, y))
        self._success.hide()
        self._failure.move((x, y))
        self._failure.hide()
        self._splot.hide()

        if self.last_pattern == self.pattern:
            self._parent.cyan.set_sensitive(True)

    def _keypress_cb(self, area, event):
        ''' Keypress: moving the slides with the arrow keys '''

        k = Gdk.keyval_name(event.keyval)
        if k in ['1', '2', '3', '4', '5']:
            self.do_stop()
            i = self._active_index
            j = int(k) - 1
            self._numbers[i][self._user_numbers[i] - 1].set_layer(HIDDEN_LAYER)
            self._numbers[i][j].set_layer(NUMBER_LAYER)
            self._user_numbers[i] = j + 1
            self.inval(self._numbers[i][j].rect)
        elif k in ['KP_Up', 'j', 'Up']:
            self.do_stop()
            i = self._active_index
            j = self._user_numbers[i]
            if j < 5:
                j += 1
            self._numbers[i][self._user_numbers[i] - 1].set_layer(HIDDEN_LAYER)
            self._numbers[i][j - 1].set_layer(NUMBER_LAYER)
            self._user_numbers[i] = j
            self.inval(self._numbers[i][j].rect)
        elif k in ['KP_Down', 'k', 'Down']:
            self.do_stop()
            i = self._active_index
            j = self._user_numbers[i]
            if j > 0:
                j -= 1
            self._numbers[i][self._user_numbers[i] - 1].set_layer(HIDDEN_LAYER)
            self._numbers[i][j - 1].set_layer(NUMBER_LAYER)
            self._user_numbers[i] = j
            self.inval(self._numbers[i][j].rect)
        elif k in ['KP_Left', 'h', 'Left']:
            self.do_stop()
            self._active_index -= 1
            self._active_index %= 5
        elif k in ['KP_Right', 'l', 'Right']:
            self.do_stop()
            self._active_index += 1
            self._active_index %= 5
        elif k in ['Return', 'KP_Page_Up', 'KP_End']:
            self.do_run()
        elif k in ['space', 'Esc', 'KP_Page_Down', 'KP_Home']:
            self.do_stop()
        else:
            logging.debug(k)

        self._canvas.grab_focus()

    def _button_press_cb(self, win, event):
        ''' Callback to handle the button presses '''
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self.press = self._sprites.find_sprite((x, y))
        if self.press is not None and self.press.type == 'number':
            self.do_stop()
            i = int(self.press.name.split(',')[0])
            self._active_index = i
            j = int(self.press.name.split(',')[1])
            j1 = (j + 1) % 5
            self._numbers[i][j1].set_layer(NUMBER_LAYER)
            self._numbers[i][j].set_layer(HIDDEN_LAYER)
            self._user_numbers[i] = j1 + 1
            self.inval(self._numbers[i][j].rect)

    def _create_results_sprites(self):
        x = 0
        y = self.sy(GY[self.i])
        self._success = Sprite(self._sprites, x, y,
                               self._parent.good_job_pixbuf())
        self._success.hide()
        self._failure = Sprite(self._sprites, x, y,
                               self._parent.try_again_pixbuf())
        self._failure.hide()

    def _create_turtle_sprites(self):
        x = self.sx(TX[self.i] - TS[self.i] / 2)
        y = self.sy(TY[self.i])
        pixbuf = self._parent.turtle_pixbuf()
        self._target_turtle = Sprite(self._sprites, x, y, pixbuf)
        self._user_turtles = []
        x = self.sx(UX[self.i] - US[self.i] / 2)
        y = self.sy(UY[self.i])
        self._user_turtles.append(Sprite(self._sprites, x, y, pixbuf))
        pixbuf = pixbuf.rotate_simple(270)
        self._user_turtles.append(Sprite(self._sprites, x, y, pixbuf))
        pixbuf = pixbuf.rotate_simple(270)
        self._user_turtles.append(Sprite(self._sprites, x, y, pixbuf))
        pixbuf = pixbuf.rotate_simple(270)
        self._user_turtles.append(Sprite(self._sprites, x, y, pixbuf))
        self._show_turtle(0)
        self._splot = Sprite(self._sprites, 0, 0, self._parent.splot_pixbuf())
        self._splot.hide()

    def _show_splot(self, x, y, dd, h):
        for i in range(4):
            self._user_turtles[i].hide()
        if h == 0:
            self._splot.move((x - int(dd / 2), y))
        elif h == 1:
            self._splot.move((x - dd, y - int(dd / 2)))
        elif h == 2:
            self._splot.move((x - int(dd / 2), y - dd))
        elif h == 3:
            self._splot.move((x, y - int(dd / 2)))
        self._splot.set_layer(SUCCESS_LAYER)
        self._failure.set_layer(SUCCESS_LAYER)

    def _show_turtle(self, t):
        for i in range(4):
            if i == t:
                self._user_turtles[i].set_layer(TURTLE_LAYER)
            else:
                self._user_turtles[i].hide()

    def _reset_user_turtle(self):
        x = self.sx(UX[self.i] - US[self.i] / 2)
        y = self.sy(UY[self.i])
        self._user_turtles[0].move((x, y))
        self._show_turtle(0)

    def _create_number_sprites(self):
        for i in range(5):
            self._numbers.append([])
            self._glownumbers.append([])
            for j in range(5):
                if self.i == 0:
                    x = self.sx(NX[self.i]) + i * (self.ss(NS[self.i]
                                                           + NO[self.i]))
                    y = self.sy(NY[self.i])
                else:
                    x = self.sx(NX[self.i])
                    y = self.sy(NY[self.i]) + i * (self.ss(NS[self.i]
                                                           + NO[self.i]))
                number = Sprite(
                    self._sprites, x, y,
                    self._parent.number_pixbuf(self.ss(NS[self.i]), j + 1,
                                              self._parent.sugarcolors[1]))
                number.type = 'number'
                number.name = '%d,%d' % (i, j)
                self._numbers[i].append(number)

                number = Sprite(
                    self._sprites, x, y,
                    self._parent.number_pixbuf(self.ss(NS[self.i]), j + 1,
                                              '#FFFFFF'))
                number.type = 'number'
                number.name = '%d,%d' % (i, j)
                self._glownumbers[i].append(number)

    def _show_user_numbers(self):
        # Hide the numbers
        for i in range(5):
            for j in range(5):
                self._numbers[i][j].set_layer(HIDDEN_LAYER)
                self._glownumbers[i][j].set_layer(HIDDEN_LAYER)
        # Show user numbers
        self._numbers[0][self._user_numbers[0] - 1].set_layer(NUMBER_LAYER)
        self._numbers[1][self._user_numbers[1] - 1].set_layer(NUMBER_LAYER)
        self._numbers[2][self._user_numbers[2] - 1].set_layer(NUMBER_LAYER)
        self._numbers[3][self._user_numbers[3] - 1].set_layer(NUMBER_LAYER)
        self._numbers[4][self._user_numbers[4] - 1].set_layer(NUMBER_LAYER)

    def _show_background_graphics(self):
        self._draw_pixbuf(
            self._parent.background_pixbuf(), 0, 0, self._width, self._height)
        self._draw_pixbuf(
            self._parent.box_pixbuf(self.ss(BS[self.i])),
            self.sx(X1[self.i]), self.sy(Y1[self.i]), self.ss(BS[self.i]),
            self.ss(BS[self.i]))
        self._draw_pixbuf(
            self._parent.box_pixbuf(self.ss(BS[self.i])),
            self.sx(X2[self.i]), self.sy(Y2[self.i]), self.ss(BS[self.i]),
            self.ss(BS[self.i]))
        self._draw_text(self.pattern, self.sx(X1[self.i]),
                        self.sy(Y1[self.i]), self.ss(LS[self.i]))

    def _set_pen_size(self, ps):
        self._cr.set_line_width(ps)

    def _set_color(self, color):
        r = color[0] / 255.
        g = color[1] / 255.
        b = color[2] / 255.
        self._cr.set_source_rgb(r, g, b)

    def _draw_line(self, x1, y1, x2, y2):
        self._cr.move_to(x1, y1)
        self._cr.line_to(x2, y2)
        self._cr.stroke()

    def ss(self, f):  # scale size function
        return int(f * self.scale)

    def sx(self, f):  # scale x function
        return int(f * self.scale + self.offset)

    def sy(self, f):  # scale y function
        return int(f * self.scale)

    def _draw_pixbuf(self, pixbuf, x, y, w, h):
        self._cr.save()
        self._cr.translate(x + w / 2., y + h / 2.)
        self._cr.translate(-x - w / 2., -y - h / 2.)
        Gdk.cairo_set_source_pixbuf(self._cr, pixbuf, x, y)
        self._cr.rectangle(x, y, w, h)
        self._cr.fill()
        self._cr.restore()

    def _draw_text(self, label, x, y, size):
        pl = PangoCairo.create_layout(self._cr)
        fd = Pango.FontDescription('Sans')
        fd.set_size(int(size) * Pango.SCALE)
        pl.set_font_description(fd)
        if type(label) == str or type(label) == unicode:
            pl.set_text(label.replace('\0', ' '), -1)
        elif type(label) == float or type(label) == int:
            pl.set_text(str(label), -1)
        else:
            pl.set_text(str(label), -1)
        self._cr.save()
        self._cr.translate(x, y)
        self._cr.set_source_rgb(1, 1, 1)
        PangoCairo.update_layout(self._cr, pl)
        PangoCairo.show_layout(self._cr, pl)
        self._cr.restore()

    def inval(self, r):
        self._canvas.queue_draw_area(r[0], r[1], r[2], r[3])

    def inval_all(self):
        self._canvas.queue_draw_area(0, 0, self._width, self._height)

    def __draw_cb(self, canvas, cr):
        cr.set_source_surface(self._turtle_canvas)
        cr.paint()

        self._sprites.redraw_sprites(cr=cr)

    def do_stop(self):
        self._parent.green.set_sensitive(True)
        self._running = False

    def do_run(self):
        self._show_background_graphics()
        # TODO: Add turtle graphics
        self._success.hide()
        self._failure.hide()
        self._splot.hide()
        self._get_goal()
        self._draw_goal()
        self.inval_all()
        self._running = True
        self.loop = 0
        self._active_index = 0
        self.step = 0
        self._set_pen_size(4)
        self._set_color(self._colors[0])
        x1 = self.sx(UX[self.i])
        y1 = self.sy(UY[self.i])
        dd = self.ss(US[self.i])
        self._numbers[0][self._user_numbers[0] - 1].set_layer(HIDDEN_LAYER)
        self._glownumbers[0][self._user_numbers[0] - 1].set_layer(NUMBER_LAYER)
        self._user_turtles[0].move((int(x1 - dd / 2), y1))
        self._show_turtle(0)

        if self._running:
            GObject.timeout_add(self.delay, self._do_step, x1, y1, dd, 0)

    def _do_step(self, x1, y1, dd, h):
        if not self._running:
            return
        if self.loop > 3:
            return
        if h == 0:  # up
            x2 = x1
            y2 = y1 - dd
            self._user_turtles[h].move((int(x2 - dd / 2), int(y2 - dd)))
        elif h == 1:  # right
            x2 = x1 + dd
            y2 = y1
            self._user_turtles[h].move((int(x2), int(y2 - dd / 2)))
        elif h == 2:  # down
            x2 = x1
            y2 = y1 + dd
            self._user_turtles[h].move((int(x2 - dd / 2), int(y2)))
        elif h == 3:  # left
            x2 = x1 - dd
            y2 = y1
            self._user_turtles[h].move((int(x2 - dd), int(y2 - dd / 2)))
        self._show_turtle(h)

        if x2 < self.sx(X2[self.i]) or \
           x2 > self.sx(X2[self.i] + BS[self.i]) or \
           y2 < self.sy(Y2[self.i]) or \
           y2 > self.sy(Y2[self.i] + BS[self.i]):
            self.do_stop()
            self._show_splot(x2, y2, dd, h)

        self._draw_line(x1, y1, x2, y2)
        self.inval_all()
        self.step += 1
        i = self._active_index
        if self.step == self._user_numbers[i]:
            number = self._user_numbers[i] - 1
            self._numbers[i][number].set_layer(NUMBER_LAYER)
            self._glownumbers[i][number].set_layer(HIDDEN_LAYER)
            h += 1
            h %= 4
            self.step = 0
            self._active_index += 1
            if self._active_index == 5:
                self.loop += 1
                self._active_index = 0
            else:
                i = self._active_index
                number = self._user_numbers[i] - 1
                self._numbers[i][number].set_layer(HIDDEN_LAYER)
                self._glownumbers[i][number].set_layer(NUMBER_LAYER)

        if self.loop < 4 and self._running:
            GObject.timeout_add(self.delay, self._do_step, x2, y2, dd, h)
        elif self.loop == 4:  # Test to see if we win
            self._running = False
            self._parent.green.set_sensitive(True)
            self._reset_user_turtle()
            self._show_user_numbers()
            self._test_level()

    def _test_level(self):
        success = True
        for i in range(5):
            if self._user_numbers[i] != self._goal[i]:
                success = False
                break
        if success:
            self._do_success()
        else:
            self._do_fail()

    def _do_success(self):
        self._success.set_layer(SUCCESS_LAYER)
        self._parent.cyan.set_sensitive(True)
        if self.last_pattern != self.pattern:
            self.score += 6
            self.last_pattern = self.pattern
        self._parent.update_score(int(self.score))

    def _do_fail(self):
        self._failure.set_layer(SUCCESS_LAYER)
        self._parent.cyan.set_sensitive(False)

    def do_slider(self, value):
        self.delay = int(value)

    def do_button(self, bu):
        self._success.hide()
        self._failure.hide()
        if bu == 'cyan':  # Next level
            self.do_stop()
            self._splot.hide()
            self.pattern += 1
            if self.pattern == 123:
                self.pattern = 1
            self._get_goal()
            self._show_background_graphics()
            self._draw_goal()
            self._reset_user_turtle()
            self.inval_all()
            self._parent.cyan.set_sensitive(False)
        elif bu == 'green':  # Run level
            self._parent.green.set_sensitive(False)
            self.do_run()
        elif bu == 'red':  # Stop level
            self.do_stop()

    def _draw_goal(self):  # draws the left hand pattern
        x1 = self.sx(TX[self.i])
        y1 = self.sy(TY[self.i])
        dd = self.ss(TS[self.i])
        dx = 0
        dy = -dd
        for i in range(4):
            for j in self._goal:
                for k in range(j):
                    x2 = x1 + dx
                    y2 = y1 + dy
                    self._set_pen_size(4)
                    self._set_color(self._colors[0])
                    self._draw_line(x1, y1, x2, y2)
                    x1 = x2
                    y1 = y2
                if dy == -dd:
                    dx = dd
                    dy = 0
                elif dx == dd:
                    dx = 0
                    dy = dd
                elif dy == dd:
                    dx = -dd
                    dy = 0
                else:
                    dx = 0
                    dy = -dd

    def _get_goal(self):
        fname = os.path.join('data', 'patterns.dat')
        try:
            f = open(fname, 'r')
            for n in range(0, self.pattern):
                s = f.readline()
            s = s[0:5]
        except:
            s = 11132
            self.pattern = 1
        f.close
        l = [int(c) for c in str(s)]
        self._goal = l
