#!/usr/bin/env python
#
#   Copyright (C) 2021 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

from flask import Flask, render_template, request, Markup
from flask_socketio import SocketIO, Namespace, emit, disconnect
import time, math, select, os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=None)

web_port = 33333

default_actions = \
    {'auto':['ir030C1000','ir030C1800','KEY_POWER','gpio17','rf7E1C2950','rf7E0C2950'],
     'menu':['ir030D1000','ir030D1800','KEY_MUTE','gpio23','rf7D1C2950','rf7D0C2950'],
     'port1':['ir03201800','ir03201000','KEY_UP','gpio27','rf771C2950','rf770C2950'],
     'starboard1':['ir03211800','ir03211000','KEY_DOWN','gpio22','rf7B1C2950','rf7B0C2950'],
     'select':['ir030B1000','ir030B1800','KEY_SELECT','gpio18','rf6F1C2950','rf6F0C2950'],
     'port10':['ir03111800','ir03111000','KEY_LEFT','gpio6','rf3F1C2950','rf3F0C2950'],
     'starboard10':['ir03101800','ir03101000','KEY_RIGHT','gpio5','rf5F1C2950','rf5F0C2950'],
     'tack':['gpio26','rf7F1C2910','rf7F0C2910']}


try:
    from flask_babel import Babel, gettext
    babel = Babel(app)

    LANGUAGES = os.listdir(os.path.dirname(os.path.abspath(__file__)) + '/translations')

    @babel.localeselector
    def get_locale():
        return request.accept_languages.best_match(LANGUAGES)
    
except Exception as e:
    print('failed to import flask_babel, translations not possible!!', e)
    def _(x): return x
    app.jinja_env.globals.update(_=_)
    babel = None

class WebConfig(Namespace):
    def __init__(self, name, pipe, config):
        super(Namespace, self).__init__(name)
        socketio.start_background_task(target=self.background_thread)
        self.pipe = pipe
        self.config = config
        self.status = 'N/A'

        self.last_key = False

        ind = 0
        acts = ['', '']
        names = Markup('[')
        cols = 1
        col = 0
        acts[ind] += Markup('<table border=0>')
        i = 0
        actions = config['actions']
        for name in actions:
            if i == 8:
                acts[ind] += Markup('</tr></table>')
                ind = 1
                acts[ind] += Markup('<table border=0>')
                col = 0
            i+=1
    
            if col == 0:
                acts[ind] += Markup('<tr>')
            acts[ind] += Markup('<td><button id="action_' + name + '">' +
                           name + '</button></td><td><span id="action' +
                           name + 'keys"></span></td>')
            if col == cols-1:
                acts[ind] += Markup('</tr>')
                col = 0
            else:
                col += 1
            names += Markup('"' + name + '", ')

        acts[ind] += Markup('</table>')

        names += Markup('""]')

        ir = Markup('<input type="radio" id="pi_ir" name="ir"')
        if config['pi.ir']:
            ir += Markup(' checked')
        ir += Markup(' /> raspberry')
        ir += Markup('<input type="radio" id="arduino_ir" name="ir"')
        if config['arduino.ir']:
            ir += Markup(' checked')
        ir += Markup(' /> arduino')
 
        nmea =  Markup('<input type="checkbox" id="arduino_nmea_in"')
        if config['arduino.nmea.in']:
            nmea += Markup(' checked')
        nmea += Markup('/> Input<input type="checkbox" id="arduino_nmea_out"')
        if config['arduino.nmea.out']:
            nmea += Markup(' checked')
        nmea += Markup('/> Output<select id="arduino_nmea_baud">')
        for baud in [4800, 38400]:
            nmea += Markup('<option value=' + str(baud))
            if baud == config['arduino.nmea.baud']:
                nmea += Markup(' selected')
            nmea += Markup('>' + str(baud) + '</option>')
        nmea += Markup('</select>')

        remote = Markup('<input type="checkbox" id="remote"')
        if config['host'] != 'localhost':
            remote += Markup(' checked')
        remote += Markup('/><input type="text" id="host" value="' + config['host'] + '">')

        @app.route('/')
        def index():
            return render_template('index.html', async_mode=socketio.async_mode, web_port=web_port, actionkeys = acts, action_names = names, ir_settings = ir, nmea_settings = nmea, remote_settings = remote)

    def on_ping(self):
        emit('pong')

    def on_keys(self, command):
        actions = self.config['actions']
        if command == 'clear':
            for name in actions:
                actions[name] = []
            self.emit_keys()
            return

        if command == 'default':
            for name in actions:
                actions[name] = []

            for name, keys in default_actions.items():
                actions[name] = keys.copy()

            self.emit_keys()
            return

        if not self.last_key:
            return
        
        # remove this key from any actions
        for name, keys in actions.items():
            while self.last_key in keys:
                keys.remove(self.last_key)

        # add the last key to the action
        actions[command].append(self.last_key)
        self.emit_keys()

    def on_config(self, config):
        self.pipe.send(config)

    def emit_keys(self):
        actions = self.config['actions']
        for name, keys in actions.items():
            keys = {'name': name, 'keys': keys}
            socketio.emit('action_keys', keys)
        self.pipe.send({'actions': actions})
        
    def on_connect(self):
        self.emit_keys()
        print('web client connected', request.sid)
        socketio.emit('status', self.status)

    def on_disconnect(self):
        print('web client disconnected', request.sid)

    def background_thread(self):
        print('web process on port', web_port)
        last_key_time = time.monotonic()
        x = 0
        polls_sent = {}
        while True:
            socketio.sleep(.5)

            if self.last_key:
                dtc = time.monotonic() - last_key_time
                if dtc > 8:
                    self.last_key = False
                    socketio.emit('key', 'N/A')
                    socketio.emit('action', '')

            if not self.pipe:
                continue

            while True:
                msg = self.pipe.recv()
                if not msg:
                    break

                if 'key' in msg:
                    self.last_key = msg['key']
                    last_key_time = time.monotonic()
                for name in msg:
                    socketio.emit(name, str(msg[name]))
                if 'status' in msg:
                    self.status = msg['status']
                    socketio.emit('status', self.status)

def web_process(pipe, config):
    print('web process', os.getpid())
    path = os.path.dirname(__file__)
    os.chdir(os.path.abspath(path))
    socketio.on_namespace(WebConfig('', pipe, config))
    socketio.run(app, debug=False, host='0.0.0.0', port=web_port)
    
if __name__ == '__main__':
    config = {'host': 'localhost', 'actions': {},
              'pi.ir': True, 'arduino.ir': False,
              'arduino.nmea.in': False, 'arduino.nmea.out': False,
              'arduino.nmea.baud': 4800,
              'lcd': {},
              'actions': default_actions.copy()}
    web_process(None, config)
