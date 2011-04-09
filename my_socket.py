import socket
import pickle
import simplejson as json
import logging
from time import sleep

import server

LOG_FILENAME = 'jukebox.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)

PORT = 8005
HEADER_LENGTH = 5




    
class MySocket(object):

    def __init__(self, my_socket=None):
        # if no socket supplied we are client create one and connect
        self.socket_open = False
        if my_socket:
            self.socket = my_socket
            self.socket_type = 'SERVER'
            self.socket_open = True
        else:
            self.socket_type = 'CLIENT'
            self.connect()

    def connect(self):
        attempt = 0
        while attempt < 5:
            attempt += 1
            try:
                logging.info('Try Connection')
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect(('', PORT))
                self.socket_open = True
            except socket.error, e:
                if e.errno == 111:
                    # connection refused
                    logging.info('connection refused at attempt %s' % attempt)
                    # try to start the server
                    if attempt == 1:
                        self.start_server()
                    sleep(1)
                    continue
                logging.exception('Socket Error\n')
                raise

    def start_server(self):
        logging.info('Trying to start server')
        server.start_daemon()



    def command(self, command_name, *args):
        packet = dict(command=command_name, args=args)
        packet = json.dumps(packet)
        self.write(packet)
        out = self.read()
        out = pickle.loads(out)
        return out

    def read(self):
        packet_length = self.read_bytes(HEADER_LENGTH)
        try:
            packet_length = int(packet_length)
        except TypeError:
            self.socket_open = False
            return
        packet = self.read_bytes(packet_length)
        return packet

    def read_bytes(self, num_bytes):
        data = ''
        while True:
            try:
                chunk = self.socket.recv(num_bytes - len(data))
            except socket.error:
                break
            if chunk == '':
                break
            data += chunk
            if len(data) == num_bytes:
                return data
        self.socket_open = False
                
    def write(self, data):
        num_bytes = len(data)
        packet = '%s' % num_bytes
        packet += ' ' * (HEADER_LENGTH - len(packet))
        self.write_bytes(packet)
        self.write_bytes(data)

    def write_bytes(self, data):
        num_bytes = len(data)
        sent_bytes = 0
        while num_bytes != sent_bytes:
            try:
                sent_bytes += self.socket.send(data[sent_bytes:])
            except socket.error:
                self.socket_open = False
                return False
        return True
