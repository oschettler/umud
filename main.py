try:
    import usocket as socket
except:
    import socket
import ujson
import sys
import ure
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
    wlan.connect(conf['ssid'], conf['pwd'))
while wlan.isconnected() == False:
    pass
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
    print(room.exits)
    exits = ''.join([
        '<li><a href="/{}">{}</a></li>'.format(x['room'], x['title']) 
        for x in room.exits])
    return html(room.title, '''
  <h1>{}</h1>
  <p>{}</p>
  <ul>{}</ul>'''.format(room.title, room.description, exits))


def create_page(name):
    return html('Create ' + name, '''
  <h1>Create {}</h1>
  <form action="/{}" method="POST">
    <input name="title" placeholder="Title"><br>
    <textarea name="description" rows="4" placeholder="Description"></textarea><br>
    <textarea name="exits" rows="4" placeholder="Exits"></textarea><br>
    <button type="submit">Save</button>
  </form>'''.format(name, name))


def name(path):
    return 'lobby' if len(path) == 1 else path[1:]
    

def get(conn, path):
    match = ure.match(r'^/create/(.+)', path)
    if match:
        response = create_page(match.group(1))
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
            conn.send('Location: /create/' + name + '\n')

    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()


def post(conn, path, vars):
    room_name = name(path)
    exits = [ line.split(None, 1) for line in vars['exits'].split(r'\n') ]
    room = Room(
       room_name,
       vars['title'],
       vars['description'],
       exits)
    room.save()
    
    response = ''
    conn.send('HTTP/1.1 302 Redirect\n') 
    conn.send('Location: ' + path + '\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()


#-------------

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    print('Got a connection from %s' % str(addr))
    request = conn.recv(2048)
    verb, path, rest = str(request).split(None, 2)
    if verb[2:] == 'POST':
        headers, vars = rest.split(r'\r\n\r\n', 1)
        vars = dict([ v.split('=') for v in vars.split('&') ])
        post(conn, path, vars)
    else:
        get(conn, path)

