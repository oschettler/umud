
import network
import socket
import machine
import time

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='MUD')
ap.config(authmode=1)

class DNSQuery:
  def __init__(self, data):
    self.data=data
    self.dominio=''

    print("Reading datagram data...")
    m = data[2] # ord(data[2])
    tipo = (m >> 3) & 15   # Opcode bits
    if tipo == 0:                     # Standard query
      ini=12
      lon=data[ini] # ord(data[ini])
      while lon != 0:
        self.dominio+=data[ini+1:ini+lon+1].decode("utf-8") +'.'
        ini+=lon+1
        lon=data[ini] #ord(data[ini])

  def respuesta(self, ip):
    packet=b''
    print("Resposta {} == {}".format(self.dominio, ip))
    if self.dominio:
      packet+=self.data[:2] + b"\x81\x80"
      packet+=self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'   # Questions and Answers Counts
      packet+=self.data[12:]                                         # Original Domain Name Question
      packet+= b'\xc0\x0c'                                             # Pointer to domain name
      packet+= b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
      packet+=bytes(map(int,ip.split('.'))) # 4 bytes of IP
    return packet

def accept_conn(listen_sock):
    cl, addr = listen_sock.accept()
    print('client connected from', addr)
    request = cl.recv(2048)
    if 'GET /?' in request:
      request = str(request)
      part = request.split(' ')[1]
      params = part.split('?')[1].split('&')
      network_param = params[0].split('=')[1]
      network_pass_param = params[1].split('=')[1]

      print("Setting network to: {}".format(network_param))

      sta_if = network.WLAN(network.STA_IF)
      sta_if.active(True)
      sta_if.connect(network_param, network_pass_param)
      while sta_if.isconnected() == False:
        time.sleep(1)

      cl.send('<html><body>Configuration Saved!<br><br>Network: {} <br>IP Address: {}<br>Password: {}<br><br><br>Restarting Device...</body></html>'.format(network_param, sta_if.ifconfig()[0], network_pass_param))
      cl.close()
      time.sleep(20)
      machine.reset()
      return

    print('Getting Network STA_IF')
    sta_if = network.WLAN(network.STA_IF)
    print('Starting Network Scan...')
    avail_networks = sta_if.scan()
    print('Network Scan Complete')

    endpoint_string = ""
    for endpoint in avail_networks:
      endpoint_string += "<option value={}>{}</option>".format(endpoint[0].decode('latin1'), endpoint[0].decode('latin1'))
    response = """
    <html>
    <head>
      <title>Mud Setup</title>
    </head>
    <body margin='10px'>
    <h2>Configure Wifi Network</h2>
    <form action='/' method='GET'>
    Network: <select name='network' id='network'>
    {}
    </select><br><br>
    Password: <input type='text' name='networkpass' id='networkpass'>
    <input type="submit">
    </form>
    </body>
    </html>
    \n\n""".format(endpoint_string)

    cl.send(response)
    time.sleep(0.001)
    cl.close()

listen_s = None

port = 80

s = socket.socket()

ai = socket.getaddrinfo("0.0.0.0", port)
addr = ai[0][4]

s.bind(addr)
s.listen(1)
s.setsockopt(socket.SOL_SOCKET, 20, accept_conn)
iface = network.WLAN(network.AP_IF)
if iface.active():
    print("Web Server daemon started on ws://%s:%d" % (iface.ifconfig()[0], port))


# def accept_dns(listen_sock):
#     cl, addr = listen_sock.accept()
#     print('DNS client connected from', addr)
#     try:
#       data, addr = udps.recvfrom(1024)
#       print("incomming datagram...")
#       p=DNSQuery(data)
#       udps.sendto(p.respuesta(ip), addr)
#       print('Replying: {:s} -> {:s}'.format(p.dominio, ip))
#     except:
#       print('No dgram')

# # SETUP DNS
# ip=ap.ifconfig()[0]
# print('DNS Server: dom.query. 60 IN A {:s}'.format(ip))

# udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# udps.setblocking(False)
# udps.bind(('',53))
# udps.setsockopt(socket.SOL_SOCKET, 20, accept_dns)
