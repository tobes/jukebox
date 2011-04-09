import threading
import socket
import simplejson as json
import pickle
import logging

import my_socket
import player

LOG_FILENAME = 'jukebox.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)


class ClientState(object):

    """ A holder of client state """

    # FIXME need to have multiple client states
    # at some time.

    def __init__(self):
        self.trigger_song_change = False 
        self.trigger_playlist_change = False 

    def song_change(self):
        self.trigger_song_change = True

    def playlist_change(self):
        self.trigger_playlist_change = True



class Server(object):

    """ A server that runs a player and allows remote connections to
        get information from and control that player.
    """

    class ServerThread(threading.Thread):

        """ The thread that handles the interactions with the player. """

        def __init__(self, client_socket=None, address=None, client_state=None, server=None):
            threading.Thread.__init__(self)
            self.client_state = client_state
            self.address = address
            self.socket = my_socket.MySocket(my_socket=client_socket)
            self.server = server

        def run(self):
            s = self.socket
            while s.socket_open:
                chunk = s.read()
                if chunk:
                    self.process(chunk)

        def process(self, data):
            """ Do the actual processing of the request made. """
            out = None
            try:
                data = json.loads(data)
                logging.debug('process data\n%s' % data)
                command = data.get('command')
                if command == 'KILL':
                    self.server.serving = False
                    self.socket.socket_open = False
                    out = 'killed'
                elif command == 'currently_playing':
                    out = self.server.my_player.currently_playing(self.client_state)
                else:
                    args = data.get('args')
                    fn = getattr(self.server.my_player, command)
                    out = fn(*args)
                out = pickle.dumps(out)
                self.socket.write(out)
            except:
                logging.exception('Process Error\nRAW DATA:\n%s\nOUT:\n%s' % (data, out))

    def __init__(self):
        self.client_state = ClientState()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', my_socket.PORT))

        self.socket.listen(5)
        self.serving = True
        self.my_player = player.Player()
        self.my_player.register_client_state(self.client_state)

        logging.info('Start serving on port %s' % my_socket.PORT)
        try:
            while self.serving:
                (client_socket, address) = self.socket.accept()
                thread = self.ServerThread(client_socket=client_socket,
                                      address=address,
                                      client_state=self.client_state,
                                      server=self)
                thread.run()
        except KeyboardInterrupt:
            logging.info('Keyboard Interrupt')
        self.my_player.stop_threads()
        logging.info('Stopped serving')



def start_daemon():
    """ Helper function to start a Server in a thread """
     
    class DaemonThread(threading.Thread):
        def run(self):
            server = Server()

    daemon = DaemonThread()
    daemon.start()


if __name__ == '__main__':
    server = Server()
