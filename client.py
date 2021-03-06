
import player
import my_socket
import logging
LOG_FILENAME = 'jukebox.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)


class Client(object):

    def __init__(self):
        self.socket = my_socket.MySocket()
        self.command = self.socket.command
        self.trigger_song_change = None
        self.trigger_playlist_change = None

    def command(self, command, *args):
        result = self.socket.command(command, *args)
        state = out[0]
        if state.trigger_song_change:
            self.trigger_song_change()
        if state.trigger_playlist_change:
            self.trigger_playlist_change()
        return out[2]



    def add_album(self, album_id):
        self.command('add_album', album_id)

    def add_song(self, song_id):
        logging.info('add_song %s' % song_id)
        self.command('add_song', song_id)

    def get_mute(self):
        return self.command('get_mute')

    def stop_threads(self):
        self.command('KILL')
        # make second request to finish the servers waiting thread
        self.command('KILL')

    def play_next(self):
        self.command('play_next')

    def mute_toggle(self):
        self.command('mute_toggle')

    def change_volume(self, amount):
        self.command('change_volume', amount)

    def currently_playing(self):
        return self.command('currently_playing')

    def get_volume(self):
        return self.command('get_volume')

    def get_cache(self, control):
        return player.Cache(control)

    def add_trigger_song_change(self, trigger):
        logging.debug('Add trigger song change')
        logging.debug(trigger)
        self.trigger_song_change = trigger
        trigger()

    def playlist_add_trigger(self, trigger):
        logging.debug('Add trigger playlist change')
        logging.debug(trigger)
        self.trigger_playlist_change = trigger
        trigger()

    def playlist_items(self):
        return self.command('playlist_items')

    def playlist_delete_item_by_position(self, position):
        pass

    def playlist_move_item_down(self, position):
        pass

    def playlist_move_item_up(self, position):
        pass
##
### database access
##self.cache = self.player.get_cache(self)
##
##self.line = self.cache.get_artists_count(tracks = self.tracks, letter = key) - 1
##self.count = self.cache.get_artists_count(tracks = self.tracks, filter = filter) + 1
##data = self.cache.get_artists(tracks = self.tracks, filter = filter)
##self.line = self.cache.get_tracks_count(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter, letter = key)
##self.count = self.cache.get_tracks_count(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter)
##data = self.cache.get_tracks(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter)
##                self.line = self.cache.get_albums_count(artist_id = self.artist_id, filter = self.filter, artist_filter = self.artist_filter, letter = key) - 1
##

