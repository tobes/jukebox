import thread
import time
import random
import re

from threading import Thread

import sqlalchemy as sa
import sqlalchemy.orm as orm


import pipe
from schema import Song, Album, Artist, History, Session
import scan
import logging

LOG_FILENAME = 'jukebox.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)

class Player(object):
    
    def __init__(self):
        self.volume = 100
        self.muted = False

        self.bonus_track = False
        self.limit_songs_mode = True
        self.limit_songs_number = 3

        self.active_player = pipe.Pipe('1')
        self.waiting_player = pipe.Pipe('2')

        self.client_states = {}

        self.playlist = PlayList(self)
        self._database = Database()

        self.alive = True

        self.current_song = None
        self.trigger_song_change = []

        self.play_next()


        # threads
        self.status_thread = StatusThread(self)
        self.scan_thread = ScanThread(self)

        self.status_thread.start()
        self.scan_thread.start()

    def register_client_state(self, client_state):
        logging.info('registering client %s' % client_state.uuid)
        self.client_states[client_state.uuid] = client_state

    def stop_threads(self):

        self.alive = False
        self.status_thread.join()
        self.scan_thread.join()

        # kill the pipes
        self.active_player.exit()
        self.waiting_player.exit()


    def get_cache(self, control):
        # FIXME simplify this or better document
        # the control interface
        return Cache(control)

    def add_trigger_song_change(self, callback):
        self.trigger_song_change.append(callback)
        # call it now to update
        callback()


    def start_stop(self):
        self.waiting_player.fadein()
        self.active_player.fadeout()
        self.swap_player()

    def swap_player(self):
        temp_player = self.active_player
        self.active_player = self.waiting_player
        self.waiting_player = temp_player


    def play(self):
        try:
            self.waiting_player.setFile(self.current_song.filename)
            self.start_stop()
            return True
        except:
            return False

    def previous(self):
        # play previous song FIXME
        pass

    def next(self):
        # play next song FIXME
        pass

    def stop(self):
        self.active_player.stop()
        self.waiting_player.stop()

    def get_duration(self):
        return self.active_player.get_duration() / 1000000000

    def get_position(self):
        return self.active_player.get_position() / 1000000000

    def get_volume(self):
        return self.volume

    def get_mute(self):
        return self.muted

    def set_volume(self, arg):
        if arg >= 0 and arg <= 100:
            self.volume = arg
            self.active_player.set_volume(self.volume)
            self.waiting_player.set_volume(self.volume)

    def change_volume(self, arg):
        volume = self.volume + arg
        if volume < 0:
            volume = 0
        elif volume > 100:
            volume = 100
        self.set_volume(volume)

    def mute_on(self):
        self.active_player.set_volume(0)
        self.waiting_player.set_volume(0)
        self.muted = True

    def mute_off(self):
        self.active_player.set_volume(self.volume)
        self.waiting_player.set_volume(self.volume)
        self.muted = False

    def mute_toggle(self):
        self.muted = not self.muted
        if self.muted:
            self.mute_on()
        else:
            self.mute_off()

    def currently_playing(self, client_state=None):
        """return data on currently playing song"""

        out = dict(item = self.current_song,
                   duration = self.get_duration(),
                   position = self.get_position())
        if client_state:
            out['trigger_song_change'] = client_state.trigger_song_change
            out['trigger_playlist_change'] = client_state.trigger_playlist_change
            client_state.trigger_song_change = False
            client_state.trigger_playlist_change = False

        return out

    def add_song(self, song_id, position = None):
        # check we are allowed to add a new song to the playlist
        if self.limit_songs_mode and self.playlist.length() >= self.limit_songs_number and not self.bonus_track:
            return
        self.bonus_track = False
        self.playlist.add_item([song_id], position)

    def trim_playlist(self):
        # trim the playlist to the number of songs allowed
        self.playlist.trim_playlist(self.limit_songs_number)

    def add_album(self, album_id):
        data = self._database.get_tracks(album_id = album_id, order = 'track')
        song_list = []
        for song, album, artist in data:
            song_list.append(song.id)
        self.playlist.add_item(song_list)


    def play_next(self):
        self.current_song = self.playlist.get_song()
        self.play()
        # triggers
        for trigger in self.trigger_song_change:
            trigger()
        for client_uuid in self.client_states:
            self.client_states[client_uuid].song_change()

##    def deleteSomeFromPlaylist(self, arg):
##        if not re.match(r'^\d+$', arg):
##            arg = 0
##        arg = int(arg) + 1
##        if arg > len(self.playlistArray):
##            arg = len(self.playlistArray)
##        self.playlistArray = self.playlistArray[:arg]
##
##    def getPlaylist(self):
##        return self.playlistArray
##
##    def getStatus(self):
##
##        status={}
##        status["position"] = self.active_player.get_position() / 1000000
##        status["duration"] = self.active_player.duration / 1000000
##        status["volume"] = self.volume
##        status["playlist"]=[]
##        for item in self.playlistArray:
##            status["playlist"] += [item["songID"]]
##        return status


    def delete_item_by_position(self, index):
        self.playlist.delete_item_by_position(index)


    def playlist_items(self):
        return self.playlist.items

class ScanThread(Thread):

    def __init__(self, player):
        Thread.__init__(self)
        self.player = player

    def run(self):
        pass
   #     scan.scan_tag(self.player, 0.025)


class StatusThread(Thread):

    def __init__(self, player):
        Thread.__init__(self)
        self.player = player


    def run(self):

        song_ending = self.player.active_player.song_ending
        check_playlist = self.player.playlist.check_playlist

        while self.player.alive:
            # sleep first
            time.sleep(1)    

            if self.player.active_player.song_ending():
                self.player.play_next()

            # check songs in playlist
            check_playlist()




class PlayListItem(object):
    """Item in the playlist"""

    def __init__(self, song_id, user_selected):

        # get song info
        session = Session()
        session.begin()

        song, artist, album = session.query(Song, Artist, Album).outerjoin(Song.song_artist).outerjoin(Song.song_album).filter(Song.id == song_id).one()

        self.song_id = song.id
        self.song_title = song.title
        self.album_id = album.id
        self.album_name = album.name
        self.album_has_art = album.art
        if artist:
            self.artist_name = artist.name
            self.artist_id = artist.id
        else:
            self.artist_name = 'unknown'
            self.artist_id = 0
        self.track = song.track
        self.filename = song.path

        # add history
        obj = History(song_id, user_selected)
        session.add(obj)
        self.history_id = id
        session.commit()
        session.close()

    def __repr__(self):
        return '<%s ~ %s>' % (self.artist_name, self.song_title)


class PlayList(object):
    """Manages the playlist allows adding, deleting of items
    including add random song"""



    def __init__(self, player):

        self.player = player
        self.items = []
        self.triggers = []
        self.random = RandomSong()

    def add_trigger(self, trigger):
        self.triggers.append(trigger)
        # call it now to update
        trigger()

    def length(self):
        return len(self.items)

    def add_item(self, song_list, position = None, user_selected = True):

        # adds songs to playlist at position
        # songs removed if already in playlist
        update = False
        for song_id in song_list:
            index = self.find_song_in_list(song_id) 
            if index != None and position == None:
                # already in the playlist and not moving so ignore
                continue
            if position == None:
                position = len(self.items)
            if index != None:
                # item already in playlist so just move it
                if position >= index:
                    position = position - 1
    
                # get item from playlist
                item = self.items.pop(index)
            else:
                # create new item
                item = PlayListItem(song_id, user_selected)
    
            # add item
            self.items.insert(position, item)
            position += 1
            update = True
        if update:
            self.playlist_update()

 
    def add_random_song(self):
        song_id = self.random.random()
        if song_id == None:
            raise Exception('No songs can be found')
        self.add_item([song_id], None, False)


    def find_song_in_list(self, song_id):
        # return index of song in playlist or None
        i = 0
        for item in self.items:
            if item.song_id == song_id:
                return i
            i += 1
        # item not found
        return None

    def delete_song(self, song_id):
        # remove song from play list if it exists
        index = self.find_song_in_list(song_id) 
        if index != None:
            item = self.items.pop(index)
        self.playlist_update()

    def delete_item_by_position(self, index):
        try:
            item = self.items.pop(index)
            self.playlist_update()
        except IndexError:
            pass

    def move_item_up(self, index):
        if index > 0:
            song_id = self.items[index].song_id
            self.add_item([song_id], index - 1, False)

    def move_item_down(self, index):
        song_id = self.items[index].song_id
        self.add_item([song_id], index + 2, False)

    def check_playlist(self):
        # if playlist is empty add a song
        while(len(self.items) < 1):
            self.add_random_song()


    def get_song(self):
        # remove first item on playlist and return it
        self.check_playlist()
        song = self.items.pop(0)

        self.playlist_update()
        return song


    def trim_playlist(self, length):
        # trim the playlist to the number of songs allowed
        self.items = self.items[:length]
        self.playlist_update()

    def playlist_update(self):
        if self.triggers:
            for trigger in self.triggers:
                trigger()

        for client_uuid in self.player.client_states:
            self.player.client_states[client_uuid].playlist_change()


class Cache(object):

    def __init__(self, control):
        self.limit = 100
        self.control = control
        self.database = Database()
        self.cache_clear()

    def cache_store(self, data):
        self.cache = data
        self.cache_start = self.cache_offset
        self.cache_end = self.cache_offset + self.limit

    def cache_limits(self):
        # get data on both sides of what we want
        self.cache_offset = self.control.offset - int((self.limit - self.control.y -2) / 2)
        if self.cache_offset < 0:
            self.cache_offset = 0
        return dict(limit = self.limit, offset = self.cache_offset)


    def cache_clear(self):
        self.cache = None
        self.cache_start = 0
        self.cache_end = 0
        self.kw = None
        self.last_call = None

    def cache_get(self):
        if not self.cache:
            return []
        if self.cache_start <= self.control.offset - self.control.min_line and self.cache_end >= self.control.offset - self.control.min_line + self.control.y - 2:
            start = self.control.offset - self.control.min_line - self.cache_start
            end = start + self.control.y - 2
            return self.cache[start:end]
        else:
            self.cache_clear()
            return []


    def cache_query(self, call, **kw):
        if kw != self.kw or call != self.last_call: 
            self.last_call = call
            self.kw = kw
            self.cache_clear()
            data = None
        else:
            data = self.cache_get()
        if not data:
            params = kw.copy()
            params.update(self.cache_limits())
            data = call(**params)
            self.cache_store(data)
            data = self.cache_get()
        return data

    # methods

    def get_artists(self, **kw):
        return self.cache_query(self.database.get_artists, **kw)

    def get_artists_count(self, **kw):
        return self.database.get_artists(count = True, **kw)

    def get_tracks(self, **kw):
        return self.cache_query(self.database.get_tracks, **kw)

    def get_tracks_count(self, **kw):
        return self.database.get_tracks(count = True, **kw)

    def get_albums(self, **kw):
        return self.cache_query(self.database.get_albums, **kw)

    def get_albums_count(self, **kw):
        return self.database.get_albums(count = True, **kw)

        
    
class Database(object):

    def __init__(self):
        self.sessions = {}

    def session(self):
        # get the correct session depending on the calling thread
        id = thread.get_ident()
        if id not in self.sessions:
            self.sessions[id] = Session()
        return self.sessions[id]

    def get_artists(self, **kw):

        data = self.session().query(Artist, sa.func.count(Song.id)).group_by(Artist.id).filter(Artist.id == Song.artist_id).order_by(Artist.name)

        if kw.get('tracks'):
            data = data.having(sa.func.count(Song.id) >= kw.get('tracks'))
        if kw.get('filter'):
            data = data.filter(Artist.name.like('%%%s%%' % kw.get('filter')))
        if kw.get('letter'):
            data = data.filter(Artist.name < kw.get('letter'))
        if kw.get('count'):
            return data.count()
        else:
            if kw.get('limit'):
                data = data.limit(kw.get('limit'))
            if kw.get('offset'):
                data = data.offset(kw.get('offset'))
            return data.all()


    def get_tracks(self, **kw):

        data = self.session().query(Song, Album, Artist).join(Song.song_album).join(Song.song_artist)
        
        order = kw.get('order')
        if order == 'track':
            data = data.order_by(Artist.name, Album.name, Song.track)
        else:
            data = data.order_by(Song.title)
        if kw.get('artist_id'):
            data = data.filter(Song.artist_id == kw.get('artist_id'))
        if kw.get('album_id'):
            data = data.filter(Song.album_id == kw.get('album_id'))
        if kw.get('filter'):
            data = data.filter(Song.title.like('%%%s%%' % kw.get('filter')))
        if kw.get('artist_filter'):
            data = data.filter(Artist.name.like('%%%s%%' % kw.get('artist_filter')))
        if kw.get('album_filter'):
            data = data.filter(Album.name.like('%%%s%%' % kw.get('album_filter')))
        if kw.get('letter'):
            data = data.filter(Song.title < kw.get('letter'))
        if kw.get('search'):
            search = '%%%s%%' % kw.get('search')
            data = data.filter(Album.name.like(search) | Artist.name.like(search) | Song.title.like(search))
        if kw.get('count'):
            return data.count()
        else:
            if kw.get('limit'):
                data = data.limit(kw.get('limit'))
            if kw.get('offset'):
                data = data.offset(kw.get('offset'))
            return data.all()



    def get_albums(self, **kw):

        data = self.session().query(Album).order_by(Album.name)

        if kw.get('artist_id'):
            data = data.filter(Album.artist_id == kw.get('artist_id'))
        if kw.get('artist_filter'):
            data = data.join(Artist).filter(Artist.name.like('%%%s%%' % kw.get('artist_filter')))
        if kw.get('filter'):
            data = data.filter(Album.name.like('%%%s%%' % kw.get('filter')))
        if kw.get('letter'):
            data = data.filter(Album.name < kw.get('letter'))
        if kw.get('count'):
            return data.count()
        else:
            if kw.get('limit'):
                data = data.limit(kw.get('limit'))
            if kw.get('offset'):
                data = data.offset(kw.get('offset'))
            return data.all()

    def get_albums_with_artist(self, **kw):

        data = self.session().query(Album, Artist).join(Album.album_artist).order_by(Artist.name, Album.name)

        if kw.get('artist_id'):
            data = data.filter(Album.artist_id == kw.get('artist_id'))
        if kw.get('artist_filter'):
            data = data.join(Artist).filter(Artist.name.like('%%%s%%' % kw.get('artist_filter')))
        if kw.get('filter'):
            data = data.filter(Album.name.like('%%%s%%' % kw.get('filter')))
        if kw.get('letter'):
            data = data.filter(Artist.name < kw.get('letter'))
        if kw.get('count'):
            return data.count()
        else:
            if kw.get('limit'):
                data = data.limit(kw.get('limit'))
            if kw.get('offset'):
                data = data.offset(kw.get('offset'))
            return data.all()





class RandomSong(object):

    attempts = 5 # number of attempts before giving up

    def random(self):

        # with lengths
        for attemp in xrange(self.attempts):
            song = self.get_song(self.full_random, True)
            if song:
                return song

        # without lengths
        for attemp in xrange(self.attempts):
            song = self.get_song(self.full_random)
            if song:
                return song

        # last ditch attempt
        for attemp in xrange(self.attempts):
            song = self.get_song(self.full_random)
            if song:
                return song


    def get_song(self, function, lengths = False):
        # return a song using the supplied function
        session = Session()
        # base query
        base = session.query(Song.id)
        # songs with lengths in a sensible range
        if lengths:
            base = base.filter(Song.length.between(30, 360))
        # add the functional extras
        base = function(base)
        # randomise the choices
        base = base.order_by(sa.func.random()).limit(1)
        # get the song
        song = base.first()
        if song:
            song_id = song.id
        else:
            song_id = None
        session.close()
        return song_id


    def full_random(self, base):
        # any song
        return base

    def directory(self, base):
        # song from directory
        return base.filter(Song.path.like('%/A/%'))

    def previously_selected(self, base):
        # previously selected
        return base.join(Song.song_history).filter(History.user_selected == True)
