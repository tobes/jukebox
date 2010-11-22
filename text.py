import time
import sys
import curses
import curses.textpad
import gobject
import player


def pretty_time(seconds):

    s = seconds % 60
    m = int(seconds / 60) % 60
    h = int(seconds / 3600)

    if not h:
        # mins: seconds
        return '%s:%02d' % (m, s)
    else:
        return '%s:%02d:%02d' % (h, m, s)


class Listing(object):

    show_all = False

    def __init__(self, parent, color = None, title = 'Title'):
        self.parent = parent
        self.player = parent.player
        self.cache = self.player.get_cache(self)
        self.color = color
        self.hotkey = None
        self.title = title
        self.win = None
        self.triggers = []
        self.search_input = None
        self.mode = 'normal'
        self.init()

    def init(self):

        if self.show_all:
            self.min_line = -1
        else:
            self.min_line = 0

        self.count = None
        self.line = self.min_line
        self.line_last = None
        self.offset = 0
        self.id = None


    def set_hotkey(self, hotkey):
        self.hotkey = hotkey

    def set_color(self, color):
        self.color = color

    def refresh(self, win):
        self.win = win
        self.y , self.x = self.win.getmaxyx()
        self.show()

    def show(self):
        if self.win:
            self.line_last = None
            self.display()

    def attach(self, control):
        self.triggers.append(control)

    def trigger(self, value, filter, name):
        pass

    def custom_key(self, key):
        pass

    def search(self, mode):
        if mode:
            self.mode = 'search'
            self.search_input = Input(self)
        else:
            self.mode = 'normal'
            self.search_input = None
            self.init()
            self.show()


    def key(self, key):
        if self.mode == 'search':
            if self.search_input.key(key):
                self.init()
                self.show()
                return
        # up
        if key == curses.KEY_UP:
            self.line -= 1
        # down
        elif key == curses.KEY_DOWN:
            self.line += 1
        # home
        elif key == curses.KEY_HOME:
            self.line = self.min_line
        # end
        elif key == curses.KEY_END:
            self.line = self.count - 1 + self.min_line
        # page up
        elif key == curses.KEY_NPAGE:
            if self.line < self.offset + self.y - 3:
                self.line = self.offset + self.y - 3
            else:
                self.line += self.y - 2
        # page down
        elif key == curses.KEY_PPAGE:
            if self.line > self.offset:
                self.line = self.offset
            else:
                self.line -= self.y - 2
        else:
            self.custom_key(key)

        self.check_line()
        self.display()

    def current_record(self):
         return self.display_count + self.offset == self.line

    def display_line(self, text):

        highlight = self.current_record()

        self.display_count += 1
        # don't write lines after window
        if self.display_count >= self.y - 1:
            return

        # trim and encode
        text = text + u' ' * (self.x - 2 - len(text))
        text = text[:self.x - 2].encode('utf-8')

        if highlight:
            self.win.attron(curses.A_STANDOUT)

        self.win.addstr(self.display_count, 1, text)

        if highlight:
            self.win.attroff(curses.A_STANDOUT)

    def check_line(self):
        if self.line < self.min_line:
            self.line = self.min_line
        # show all funniness
        if  self.show_all:
            if self.count <= self.y:
                offset =  -2
            else:
                offset =  -3
        else:
            offset = -1
        if self.line > self.count + offset:
            self.line = self.count + offset



    def display(self):


        # no movement do nothing
        if self.line == self.line_last:
            return

        # do we need to scroll the screen?
        self.line_last = self.line

        if self.line < self.min_line:
            self.line = self.min_line
        if self.line < self.offset:
            self.offset = self.line 
        elif self.line >= self.offset + self.y - 2:
            self.offset = self.line - self.y + 3

        self.win.erase()
        if self.color != None:
            self.win.attron(curses.color_pair(self.color))
        self.win.box()
        if self.hotkey:
            self.win.addstr(0, 1, self.hotkey)
            self.win.addstr(0, 3, self.title)
        else:
            self.win.addstr(0, 1, self.title)
            
        self.display_count = 0

        if self.show_all and self.offset == -1:
            self.display_line('(All)')

        self.display_data()

        if self.count != None:
            # scroll indicator
            if self.count and self.count - self.min_line > self.y - 2:
                percent = float(self.line) / self.count
                position = int((self.y - 2) * percent) + 1
                if self.y > 2:
                    self.win.addstr(position, self.x - 1, '+')
            # counter wierdness
            if self.show_all and self.count > self.y:
                info = '[%s/%s]' % (self.line + 1, self.count - 2)
            else:
                info = '[%s/%s]' % (self.line + 1, self.count + self.min_line)
            self.win.addstr(0, self.x - len(info) - 1, info)

        if self.mode == 'search':
            self.search_input.show()
            filter = self.search_input.text
        else:
            filter = None

        if self.color != None:
            self.win.attroff(curses.color_pair(self.color))
        self.win.refresh()

        # triggers
        for control in self.triggers:
            control.trigger(self.id, filter, self.data)

    def display_data(self):
        pass

class Input(object):

    def __init__(self, parent):
        self.parent = parent
        self.win = parent.win
        self.length = 15
        self.position = 0
        self.text = ''
        curses.curs_set(2)

    def key(self, key):
        old_text = self.text
        if 31 < key < 128:
            self.text = self.text[:self.position] + chr(key) + self.text[self.position:]
            self.position += 1
        elif key == curses.KEY_LEFT:
            self.position -= 1
        elif key == curses.KEY_RIGHT:
            self.position += 1
        elif key == curses.KEY_HOME:
            self.position = 0
        elif key == curses.KEY_END:
            self.position = self.length
        elif key == curses.KEY_DC:
            self.text = self.text[:self.position] + self.text[self.position + 1:]
        elif key == curses.KEY_BACKSPACE:
            self.text = self.text[:self.position - 1] + self.text[self.position:]
            self.position -= 1

        # sanity check
        self.text = self.text[:self.length]
        if self.position >= self.length:
            self.position = self.length - 1
        elif self.position >= len(self.text):
            self.position = len(self.text)
        elif self.position < 0:
            self.position = 0
        return old_text != self.text
            
    def show(self):
        win = self.win.derwin(1, self.length + 2, self.parent.y - 1, self.parent.x - self.length - 2)
        win.addstr(0, 0, '/' + self.text + ' ' * (self.length - len(self.text)))
        # position the cursor
        win.move(0, self.position + 1)
        win.refresh()




class Artists(Listing):


    data = 'artist'
    tracks = 1

    show_all = True


    def custom_key(self, key):
    
        update = False
        if key < 256:
            key = chr(key).upper()
            if key >= 'A' and key <= 'Z':
                self.line = self.cache.get_artists_count(tracks = self.tracks, letter = key) - 1
                update = True
            if key == '#':
                self.line = 0
                update = True
        if update:
            self.offset = self.line
            if self.offset > self.count - self.y:
                self.offset = self.count - self.y
            self.check_line()
            self.display()

    def display_data(self):

        if self.search_input:
            filter = self.search_input.text
        else:
            filter = None

        if self.count == None:
            self.count = self.cache.get_artists_count(tracks = self.tracks, filter = filter) + 1
        data = self.cache.get_artists(tracks = self.tracks, filter = filter)

        self.id = None

        for artist, num_tracks in data:
            text = u'%ls (%ls)' % (artist.name, num_tracks)
            if self.current_record():
                self.id = artist.id
            self.display_line(text)



class Tracks(Listing):

    artist_id = None
    album_id = None
    album_filter = None
    artist_filter = None
    filter = None

    def custom_key(self, key):

        update = False
        # ENTER add song
        if key == 10:
            self.player.add_song(self.id)
        if key < 256:
            key = chr(key).upper()
            if key >= 'A' and key <= 'Z':
                self.line = self.cache.get_tracks_count(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter, letter = key)
                update = True
            if key == '#':
                self.line = 0
                update = True
        if update:
            self.offset = self.line
            if self.offset > self.count - self.y:
                self.offset = self.count - self.y
            self.check_line()
            self.display()


    def trigger(self, value, filter, name):

        update = False
        if name == 'artist' and (self.artist_id != value or self.artist_filter != filter):
            self.artist_filter = filter
            self.artist_id = value
            update = True
        if name == 'album' and (self.album_id != value or self.album_filter != filter):
            self.album_filter = filter
            self.album_id = value
            update = True
        if update:
            self.init()
            self.show()

    def display_data(self):

        if self.search_input:
            self.filter = self.search_input.text
        else:
            self.filter = None

        if self.count == None:
            self.count = self.cache.get_tracks_count(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter)

        data = self.cache.get_tracks(artist_id = self.artist_id, album_id = self.album_id, filter = self.filter, artist_filter = self.artist_filter, album_filter = self.album_filter)

        self.id = None

        if not data:
            return
        for song, album, artist in data:
            if song.length:
                text = u'%ls [%s]' % (song.title, pretty_time(song.length))
            else:
                text = u'%ls' % (song.title)

            
            if self.current_record():
                self.id = song.id
            self.display_line(text)



class Albums(Listing):

    data = 'album'
    artist_id = None
    artist_filter = None
    filter = None

    show_all = True

    def custom_key(self, key):
        update = False
        if key < 256:
            key = chr(key).upper()
            if key >= 'A' and key <= 'Z':
                self.line = self.cache.get_albums_count(artist_id = self.artist_id, filter = self.filter, artist_filter = self.artist_filter, letter = key) - 1
                update = True
            if key == '#':
                self.line = 0
                update = True
        if update:
            self.offset = self.line
            if self.offset > self.count - self.y:
                self.offset = self.count - self.y
            self.check_line()
            self.display()

    def trigger(self, value, filter, name):
        if self.artist_id != value or self.artist_filter != filter:
            self.artist_id = value
            self.artist_filter = filter
            self.init()
            self.show()

    def display_data(self):

        if self.search_input:
            self.filter = self.search_input.text
        else:
            self.filter = None

        if self.count == None:
            self.count = self.cache.get_albums_count(artist_id = self.artist_id, filter = self.filter, artist_filter = self.artist_filter) + 1


        data = self.cache.get_albums(artist_id = self.artist_id, filter = self.filter, artist_filter = self.artist_filter)

        self.id = None


        for album in data:
            text = u'%ls' % album.name
            if self.current_record():
                self.id = album.id
            self.display_line(text)



class Playlist(Listing):

    def custom_key(self, key):
        if key < 256:
            key = chr(key).upper()
            if key == 'D':
                self.player.playlist.delete_item_by_position(self.line)


    def display_data(self):
        playlist = self.player.playlist.items

        self.count = len(playlist)
        for item in playlist[self.offset:self.y - 2 + self.offset]:
            text = u'%ls ~ %ls' % (item.artist_name, item.song_title)
            if self.current_record():
                self.id = item.song_id
            self.display_line(text)


    def search(self, mode):
        pass


class Interface(object):

    def __init__(self, stdscr):

        self.stdscr = stdscr
        stdscr.nodelay(1)
        curses.curs_set(0)
        gobject.threads_init()
        self.player = player.Player()
        #self.player.mute_toggle()

        # set up controls
        self.artists_control = Artists(self, color = 2, title = 'Artists')
        self.tracks_control = Tracks(self, color = 2, title = 'Tracks')
        self.albums_control = Albums(self, color = 2, title = 'Albums')
        self.playlist_control = Playlist(self, color = 2, title = 'Playlist')

        # join controls
        self.artists_control.attach(self.tracks_control)
        self.artists_control.attach(self.albums_control)
        self.albums_control.attach(self.tracks_control)

        # get playlist to update on changes
        self.player.playlist.add_trigger(self.playlist_control.show)
        # update current trigger
        self.player.add_trigger_song_change(self.show_playing)

        # build tabs
        self.tabs = []
        self.tabs.append(dict(control = self.artists_control, key = '2'))
        self.tabs.append(dict(control = self.albums_control, key = '3'))
        self.tabs.append(dict(control = self.tracks_control, key = '4'))
        self.tabs.append(dict(control = self.playlist_control, key = '1'))
        self.current_tab = 0
        self.status = 'Welcome to jukebox hope you are having lots of fun ;)'
        self.status_last = None
        self.status_position = 0.0

        self.init()

    def init(self):
        y, x = self.stdscr.getmaxyx()
        self.x = x
        self.y = y
        self.status_offset = self.x

        # set up colors
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_BLUE)
        self.stdscr.addstr(0, 0, "Jukebox", curses.color_pair(1))
        self.stdscr.addstr(0, 7, " " * (self.x - 7), curses.color_pair(1))
        self.stdscr.refresh()

        self.current = curses.newwin(5, self.x, 1, 0)
        self.show_playing()

        self.make_windows()
        self.show_current()

        # select tab
        self.set_active_tab()

    def make_windows(self):
        # set up windows

        start = 5
        end = 1

        space = self.y - start - end

        amount = int(space / 4)

        size_playlist = amount
        start_playlist = 5
        size_artists = amount
        start_artists = start_playlist + size_playlist
        size_albums = amount
        start_albums = start_artists + size_artists
        size_tracks = space - size_playlist - size_artists - size_albums
        start_tracks = start_albums + size_albums

        self.win_playlist = curses.newwin(size_playlist, self.x, start_playlist, 0)
        self.win_artists = curses.newwin(size_artists, self.x, start_artists, 0)
        self.win_albums = curses.newwin(size_albums, self.x, start_albums, 0)
        self.win_tracks = curses.newwin(size_tracks, self.x, start_tracks, 0)
        self.win_status = curses.newwin(end + 1, self.x, self.y - 1, 0)
        
        # show windows
        self.artists_control.refresh(self.win_artists)
        self.tracks_control.refresh(self.win_tracks)
        self.albums_control.refresh(self.win_albums)
        self.playlist_control.refresh(self.win_playlist)


    def show_playing(self):
        try:
            current = self.player.currently_playing()
            if current:
                item = current['item']
                title = item.song_title
                artist = item.artist_name
                track = item.track
                album = item.album_name
    
                # display track info
                text = u"%s ~ %s" % (artist, album)
                self.current.addstr(0, 0, text[:self.x].encode('utf-8'), curses.color_pair(2))
                self.current.clrtoeol()
                text = u"%s. %s" % (track, title)
                self.current.addstr(1, 0, text[:self.x].encode('utf-8'), curses.color_pair(2))
                self.current.clrtoeol()
    
                self.current.refresh()
        except AttributeError:
            pass


    def show_current(self):
        current = self.player.currently_playing()
        if current:
            duration = current['duration']
            position = current['position']

            #self.current.erase()

            self.current.addstr(2, 0, "%s %s" % (pretty_time(duration), pretty_time(position)), curses.color_pair(2))
            self.current.clrtoeol()

            #volume
            if self.player.get_mute():
                volume = 'MUTE'
            else:
                volume = '%s%%' % self.player.get_volume()
            self.current.addstr(2, self.x - len(volume), volume, curses.color_pair(2))


            # progress bar
            if duration:
                bar_length = int(self.x * (float(position) / duration))
            else:
                bar_length = 0
            bar = pretty_time(position) #pretty_time(duration),
            # centre the time info
            if len(bar) < self.x:
                bar = ' ' * int((self.x - len(bar)) / 2) + bar
                bar = bar + ' ' * (self.x - len(bar))
            # draw the progess indicator
            self.current.attron(curses.color_pair(3))
            self.current.addstr(3, 0, bar[:bar_length])
            self.current.attron(curses.A_STANDOUT)
            self.current.addstr(3, bar_length, bar[bar_length:])
            self.current.attroff(curses.A_STANDOUT)
            self.current.attroff(curses.color_pair(3))
            self.current.refresh()

        #    self.show_status()

            if self.tabs[self.current_tab]['control'].search_input:
                self.tabs[self.current_tab]['control'].search_input.show()
            else:
                curses.curs_set(0)

    def show_status(self):

        speed = 0.3
        
        if self.status_offset > 0:
            self.status_offset -= speed
            position = 0
        else:
            self.status_offset = 0

            self.status_position += speed
            position = int(self.status_position)
        text = self.status[position:position + self.y - int(self.status_offset)]



        self.win_status.clear()
        self.win_status.addstr(0, int(self.status_offset), text)
        self.win_status.clrtoeol()
        self.win_status.refresh()


        if position > len(self.status) + 1:
            self.status_position = 0
            self.status_offset = self.x

    def search(self):
        self.win_search = curses.newwin(1, 10, 0, self.x - 11)
        search_box = curses.textpad.Textbox(self.win_search)
        search = search_box.edit()

    def key_event(self, key):
        # ESC
        if key == 27:
            self.player.stop_threads()
            sys.exit()
        # TAB
        if key == 9:
            self.current_tab += 1
            if self.current_tab >= len(self.tabs):
                self.current_tab = 0
            self.set_active_tab()
            return
        # Shift TAB
        elif key == curses.KEY_BTAB:
            self.current_tab -= 1
            if self.current_tab <0:
                self.current_tab = len(self.tabs) - 1
            self.set_active_tab()
            return
        if self.tabs[self.current_tab]['control'].mode != 'search':
            # move tabs
            tab_count = 0
            for tab in self.tabs:
                if key == ord(tab['key']):
                    self.current_tab = tab_count
                    self.set_active_tab()
                    break
                tab_count += 1


            if key == curses.KEY_RESIZE:
                self.init()
            elif key == ord('>') or key == ord('.'):
                self.player.play_next()
            elif key == ord('0') or key == ord(')'):
                self.player.mute_toggle()
            elif key == ord('+') or key == ord('='):
                self.player.change_volume(5)
            elif key == ord('-') or key == ord('_'):
                self.player.change_volume(-5)
            elif key == ord('/') or key == ord('?'):
                self.tabs[self.current_tab]['control'].search(True)
            # pass to active tab
            else:
                self.tabs[self.current_tab]['control'].key(key)
        # pass to active tab
        else:
            if key == ord('/') or key == ord('?'):
                self.tabs[self.current_tab]['control'].search(False)
            else:
                self.tabs[self.current_tab]['control'].key(key)

    def set_active_tab(self):

        count = 0
        for tab in self.tabs:
            if self.current_tab == count:
                # active
                tab['control'].set_color(2)
            else:
                # inactive
                tab['control'].set_color(5)
            tab['control'].set_hotkey(tab['key'])
            tab['control'].show()
            count += 1

    def main(self):
        while True:
            try:
                key = self.stdscr.getch()
                if key > -1:
                    # clear input
                    curses.flushinp()
                    self.key_event(key)
                else:
                    time.sleep(0.1)
                # debug info
          #      self.stdscr.addstr(46, 0, '%s    ' % key)
          #      self.stdscr.addstr(47, 0, '%s   %s ' % (self.current_tab, self.tabs[self.current_tab].color))
                self.show_current()
            except KeyboardInterrupt:
                self.player.stop_threads()
                sys.exit()

def init(stdscr):
    interface = Interface(stdscr)
    interface.main()

def start():
    curses.wrapper(init)

if __name__ == '__main__':
    start()



