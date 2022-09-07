#!/usr/bin/env python
#
#   Copyright (C) 2016 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import wx, wx.glcanvas, sys, socket, time, os
from OpenGL.GL import *
from pypilot.client import pypilotClientFromArgs

import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scope_ui import pypilotScopeBase
from scope import pypilotPlot

def wxglutkeypress(event, special, key):
    translation = { wx.WXK_UP : GLUT_KEY_UP, wx.WXK_DOWN : GLUT_KEY_DOWN, \
                    wx.WXK_LEFT : GLUT_KEY_LEFT, wx.WXK_RIGHT : GLUT_KEY_RIGHT, \
                    wx.WXK_INSERT : GLUT_KEY_INSERT, wx.WXK_DELETE : GLUT_KEY_DELETE}
    if event.GetKeyCode() in translation:
        special(translation[event.GetKeyCode()], event.GetPosition().x, event.GetPosition().y)
    else:
        code = event.GetKeyCode()
        if code < 255:
            k = '%c' % code
            if not event.GetModifiers() & wx.MOD_SHIFT:
                k = k.lower()
            key(k, event.GetPosition().x, event.GetPosition().y)

class pypilotScope(pypilotScopeBase):
    def __init__(self):
        super(pypilotScope, self).__init__(None)

        self.plot = pypilotPlot()
        self.glContext =  wx.glcanvas.GLContext(self.glArea)

        host = False
        self.args = []
        if len(sys.argv) > 1:
            host, self.args = sys.argv[1], sys.argv[2:]
        self.client = pypilotClientFromArgs(self.args, host=host)
        self.client.watch('timestamp')
        self.watches = {}

        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.receive_messages, id=wx.ID_ANY)
        self.timer.Start(100)

        self.sTime.SetValue(self.plot.disptime)
        self.plot_reshape = False

    def enumerate_values(self, value_list):
        watches = self.args
        for name in sorted(value_list):
            if value_list[name]['type'] != 'SensorValue' or name == 'timestamp':
                continue

            i = self.clValues.Append(name)
            self.watches[name] = False
            for arg in watches:
                if arg == name:
                    self.clValues.Check(i, True)
                    self.watches[name] = True
                    watches.remove(name)
                    break

        if watches:
            print(_('values not found:'), watches)
                
    def receive_messages(self, event):
        if not self.client:
            try:
                host, port = self.host_port
                self.client = pypilotClient(self.on_con, host, port, autoreconnect=False)
                self.timer.Start(50)
            except socket.error:
                self.timer.Start(1000)
                return

        if not self.plot.value_list:
            value_list = self.client.list_values()
            if value_list:
                self.enumerate_values(value_list)
                self.plot.init(value_list)
            return
            
        refresh = False
        self.client.poll()

        if not self.client.connection:
            self.plot.add_blank()
            return
            
        while True:
            result = self.client.receive_single()
            if not result:
                break

            name, value = result
            if name == 'timestamp' or self.watches[name]:
                if self.plot.read_data(result):
                    refresh = True

        if refresh:
            self.glArea.Refresh()

    def onValueSelected( self, event ):
        self.plot.select(self.clValues.GetStringSelection())

    def onValueToggled( self, event ):
        value = self.clValues.IsChecked(event.GetInt())
        self.watches[event.GetString()] = value
        self.client.watch(event.GetString(), value)
        self.plot.add_blank(event.GetString())

    def onPaintGL( self, event ):
        dc = wx.PaintDC( self.glArea )
        self.glArea.SetCurrent(self.glContext)
        self.plot.fft_on = self.cbfftw.GetValue()

        if self.plot_reshape:
            self.plot.reshape(*self.plot_reshape)
            self.plot_reshape = False

        self.plot.display()
        self.glArea.SwapBuffers()

    def onSizeGL( self, event ):
        self.plot_reshape = (event.GetSize().x, event.GetSize().y)

    def onMouseEvents( self, event ):
        self.glArea.SetFocus()

        pos = event.GetPosition()
        if event.LeftDown():
            self.lastmouse = pos

        if event.RightDown():
            self.plot.curtrace.center()
            self.glArea.Refresh()

        if event.Dragging():
            offset = pos[1] - self.lastmouse[1]
            self.plot.adjustoffset(offset, self.glArea.GetSize().y)
            self.lastmouse = pos
            self.glArea.Refresh()

        rotation = event.GetWheelRotation() / 60
        if rotation:
            if rotation > 0:
                self.plot.increasescale()
            else:
                self.plot.decreasescale()
            self.glArea.Refresh()

    def onKeyPress( self, event ):
        wxglutkeypress(event, self.plot.special, self.plot.key)
        self.cbfftw.SetValue(self.plot.fft_on)
        self.glArea.Refresh()

    def onZero( self, event ):
        if self.plot.curtrace:
            self.plot.curtrace.offset = 0
            self.glArea.Refresh()

    def onCenter( self, event ):
        if self.plot.curtrace:
            self.plot.curtrace.center()
            self.glArea.Refresh()

    def onScalePlus( self, event ):
        self.plot.increasescale()
        self.glArea.Refresh()

    def onScaleMinus( self, event ):
        self.plot.decreasescale()
        self.glArea.Refresh()

    def onOffsetPlus( self, event ):
        self.plot.curtrace.offset -= self.plot.scale/10.0
        self.glArea.Refresh()
            
    def onOffsetMinus( self, event ):
        self.plot.curtrace.offset += self.plot.scale/10.0
        self.glArea.Refresh()

    def onFreeze( self, event ):
        self.plot.freeze = event.IsChecked()
        self.glArea.Refresh()

    def onReset( self, event ):
        self.plot.reset()
        self.glArea.Refresh()

    def onTime(self, event):
        self.plot.disptime = self.sTime.GetValue()
        self.glArea.Refresh()

    def onClose( self, event ):
        self.Close()
	
from OpenGL.GLUT import *
def main():
    glutInit(sys.argv)
    app = wx.App()
    pypilotScope().Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
