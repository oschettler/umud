try:
    import usocket as socket
except:
    import socket
import ujson
import sys
import ure
from utils import unquote

if GO:
    GO.lcd.clear()
    GO.lcd.font(GO.lcd.FONT_DejaVu24, color=GO.lcd.GREEN)
else:
    import ssd1306
    from machine import I2C, Pin
    i2c=I2C(-1, Pin(5), Pin(4))
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.fill(0)

from random import getrandbits
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
with open('wlan.json') as f:
    conf = ujson.load(f)
    wlan.connect(conf['ssid'], conf['pwd'])
while wlan.isconnected() == False:
    pass

if GO:
    GO.lcd.text(GO.lcd.CENTER, GO.lcd.CENTER, wlan.ifconfig()[0])
else:
    display.text(wlan.ifconfig()[0], 0, 0)
    display.show()

class Room:
    def __init__(self, name, title, description, exits):
        self.name = name
        self.title = title
        self.description = description
        self.exits = exits

    @staticmethod
    def load(name):
        fname = 'rooms/' + name + '.json'
        try:
            with open(fname) as f:
                data = ujson.load(f)
                return Room(
                    name,
                    data['title'],
                    data['description'],
                    data['exits']
                )
        except OSError:
            return None

    def save(self):
        fname = 'rooms/' + self.name + '.json'
        with open(fname, 'w') as f:
            ujson.dump({
                "title": self.title,
                "description": self.description,
                "exits": self.exits
            }, f)

    def exits_html(self):
        print(self.exits)
        return ''.join([
        '<li><a href="/{}">{}</a></li>'.format(room, title)
        for room, title in self.exits.items()]) 

    def exits_text(self):
        return '\n'.join(['{} {}'.format(room, title)
        for room, title in self.exits.items()])


def html(title, body):
    return '''<html><head><title>{} - ESPmud</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta charset="UTF-8">
</head>
<body>
{}
</body>
</html>'''.format(title, body)


def room_page(room):
    return html(room.title, '''
  <h1>{} <a href="/edit/{}">✎</a></h1>
  <p>{}</p>
  <ul>{}</ul>'''.format(room.title, room.name, room.description, room.exits_html()))


def room_form(name, room=None):
    verb = 'Edit' if room else 'Create'
    title = room.title if room else ''
    description = room.description if room else ''
    exits = room.exits_text() if room else ''

    return html(verb + ' ' + name, '''
  <h1>{} {}</h1>
  <form action="/{}" method="POST">
    <input name="title" placeholder="Title" value="{}"><br>
    <textarea name="exits" rows="4" placeholder="Exits">{}</textarea><br>
    <textarea name="description" rows="4" placeholder="Description">{}</textarea><br>
    <button type="submit">Save</button>
  </form>'''.format(verb, name, name, title, exits, description))


def name(path):
    return 'lobby' if len(path) == 1 else path[1:]
    

def get(conn, path):
    match = ure.match(r'^/edit/(.+)', path)
    if match:
        room_name = match.group(1)
        room = Room.load(room_name)
        if room:
            response = room_form(room_name, room)
        else:
            response = room_form(room_name)
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
    else:
        room_name = name(path)
        room = Room.load(room_name)
        if room:
            response = room_page(room)
            conn.send('HTTP/1.1 200 OK\n')
            conn.send('Content-Type: text/html\n')
        else:
            response = ''
            conn.send('HTTP/1.1 302 Redirect\n')
            conn.send('Location: /edit/' + room_name + '\n')

    try:
        conn.send('Connection: close\n\n')
        conn.sendall(response)
    except OSError:
        print("ERR: Timeout")
    finally:
        conn.close()


def post(conn, path, vars):
    conn.send('HTTP/1.1 302 Redirect\n')
    room_name = name(path)
    try:
        exits = dict([ line.split(None, 1) for line in vars['exits'].split('\r\n') ])
    except:
        conn.send('Location: /edit/' + room_name + '\n')
    else:
        room = Room(
            room_name,
            vars['title'],
            vars['description'],
            exits)
        room.save()
    
    conn.send('Location: ' + path + '\n')
    conn.send('Connection: close\n\n')

    try:
        conn.sendall('')
    except OSError:
        print("Timeout")
    finally:
        conn.close()


#-------------

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    print('Got a connection from %s' % str(addr))
    request = str(conn.recv(2048))

    print(request)

    try:
        verb, path, rest = str(request).split(None, 2)
    except:
        print("ERR: Empty request")
        continue

    if verb[2:] == 'POST':
        headers, vars = rest[:-1].split(r'\r\n\r\n', 1)
        vars = dict([ v.split('=') for v in vars.split('&') ])
        for key, value in vars.items():
            vars[key] = unquote(value.replace('+', ' ')).decode('utf-8')
        print(vars)
        post(conn, path, vars)
    else:
        get(conn, path)

