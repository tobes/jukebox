#!/usr/bin/env python

import pygtk, os.path, thread, time
pygtk.require('2.0')
import gtk, pango, string, random, gobject
import player, re

version = "0.3.6 alpha"
app_path = os.path.dirname(os.path.abspath(__file__))


from schema import Song, Album, Artist, History, Session

class jukebox:


    dragSongID = 0
    dragDelete = False
    fullscreen_mode = False
    playlistArray = []
    playlistPosition = -1
    keylogger = ""
    statusTimeToggle = True
    msg_window_active = False
    admin_mode = True
    admin_password = "fish"
    bonus_track = False
    limit_songs_mode = True
    limit_songs_number = 3
    

    currentOffset = 0
    currentWhere = ""
    currentFunction = ""


    currentAlbumID = 0

    def format_time(self, time):
        # format time as min:sec
        time_mins = int(time/60)
        time_secs = int((time % 60))
        return "%d:%02d" % (time_mins, time_secs)

    def html_encode(self, arg):
        arg=string.replace(arg, "&", "&amp;")
        arg=string.replace(arg, "<", "&lt;")
        arg=string.replace(arg, ">", "&gt;")
        return arg

    def getMatchColour(self, match):
        if match == None:
            colour="black"
        else:
            if match == 100:
                colour="DarkGreen"
            elif match > 80:
                colour="ForestGreen"
            elif match > 50:
                colour="darkorange"
            else:
                colour="red"
        return gtk.gdk.color_parse(colour)


    def delete_event(self, widget, event, data = None):
        self.player.stop_threads()
        gtk.main_quit()

    def destroy(self, widget, data = None):
        self.player.stop_threads()
        gtk.main_quit()

    def setCurrentTrack(self):
        current = self.player.currently_playing()
        if current:
            item = current['item']
            title = item.song_title
            artist = item.artist_name
            track = item.track
            album = item.album_name
            album_id = item.album_id
            art = item.album_has_art

        
            self.statusArtist.set_text(artist)
            self.statusAlbum.set_text(album)
            self.statusTrack.set_text(title)
            self.setAlbumArt(self.statusArt, art, album_id, 180)
            self.currentAlbumID = album_id


    # STATUS
    # ======================================
    
    def status(self):
        self.panesize_temp = 0  # detect when pane resized need to do this properly
        # FIXME want to have a cleaner thread exit here
        while True:            
            track_length = self.player.get_duration()
            track_time = self.player.get_position()
            if self.statusTimeToggle:
                timeRemaining = track_length - track_time
            else:
                timeRemaining = track_time
            self.statusTimeLabel.set_text(self.format_time(timeRemaining))
            if track_time>0: # don't want a divide by zero
                self.statusProgress.set_fraction(1.0 - float(track_length - track_time) / track_length)
            else:
                self.statusProgress.set_fraction(0)

            # panesize stuff to be removed when implemented better
            if self.panesize != self.pane2.get_position():
                if self.panesize_temp == self.pane2.get_position():
                    self.pane_timer = self.pane_timer + 1
                    if self.pane_timer >= 10:
                        self.panesize = self.pane2.get_position()
                        self.actionFillAlbums(self.currentWhere, self.currentOffset - 16)
                else:
                    self.panesize_temp = self.pane2.get_position()
                    self.pane_timer = 0
            time.sleep(0.1)    
            

    # CONTROLS
    # ======================================



    def volumeChange(self, widget, data = None):
        # volume changes
        self.player.set_volume(int(self.ctlVol.get_value()))

    def butMute(self, widget, data = None):
        # mute button
        self.player.mute_toggle()

    def butPlay (self, widget, data = None):
        #  button
        pass

    def butPrev (self, widget, data = None):
        #  button
        pass

    def butNext (self, widget, data = None):
        #  button
        self.player.play_next()

    def butStop (self, widget, data = None):
        #  button
        self.player.stop()

    def butFullScreen(self, widget, data = None):
        self.fullscreen_mode = not self.fullscreen_mode
        if self.fullscreen_mode:
            self.window.fullscreen()
        else:
            self.window.unfullscreen()


    def eventPress(self, widget, data = None, i = ""):
        (a, b) = self.artistSubHolder.get_selection().get_selected()
        self.fillTracks(dict(artist_id = a.get_value(b, 1), order = 'track'))
        self.window.show_all()
        # move the albums too first get the artist name to use
        artist = a.get_value(b, 0)
        artist = re.sub(r' \(\d*\)$', "", artist)
        self.fillAlbums(artist)

    def eventIn(self, widget, data = None):
        widget.set_state(gtk.STATE_PRELIGHT)

    def eventOut(self, widget, data = None):
        widget.set_state(gtk.STATE_NORMAL)

    def eventChange(self, widget, data=None):
        self.fillArtists(int(widget.get_active_text()))
        self.window.show_all()


    # PLAY SONGS
    # ======================================
    def play_album(self, album_id):
        self.player.add_album(album_id)

    def play_song_callback(self, widget, data = None, song_id = 0):
        # add song to playlist
        # make sure we double clicked
        if data.button == 1 and data.type == gtk.gdk._2BUTTON_PRESS:
            self.player.add_song(song_id)
        
        if data.button == 3: # right click

            menu=gtk.Menu()

            menu_items = gtk.MenuItem("Play song")
            menu_items.connect("button_press_event", self.menu_callback_play_song, (int(song_id)))
            menu.append(menu_items)

            menu.show_all()
            menu.popup(None, None, None, data.button, data.time)
        return False


    def menu_callback_play_song(self, widget, data = None, info = None):
        self.player.add_song(info)


    def deleteAllFromPlaylist(self):
        self.playlistArray = self.playlistArray[:0]



    # ARTIST LIST
    # ======================================

    def fillArtists(self, songs):
        self.actionFillArtists(songs)

    def actionFillArtists(self, songs):
        # clear out the subartistHolder to hold artist list
        self.artistList.clear()
        data = self.database.get_artists(tracks = songs)

        # output
        for artist, count in data:
            info = '%s (%s)' % (artist.name, count)
            self.artistList.append([info, artist.id])

    # PLAYLIST
    # ======================================

    def playlistSendCallback(self, widget, context, selection, targetType, eventTime):
        self.dragSongID = targetType    
        self.dragDelete = True
        selection.set(selection.target, 8, "str")

    def tracklistSendCallback(self, widget, context, selection, targetType, eventTime):
        self.dragSongID = targetType    
        self.dragDelete = False
        selection.set(selection.target, 8, "str")

    def currentReceiveCallback(self, widget, context, x, y, selection, targetType, time):    
        # play the song now
        self.deleteFromPlaylist(self.dragSongID)

    def playlistReceiveCallback(self, widget, context, x, y, selection, targetType, time):
        position = (y // 61)
        self.player.add_song(self.dragSongID, position)

    def tracklistDragEnd(self,widget, drag_context, data = ""):
        self.OutPlaylist()

    def playlistDragEnd(self,widget, drag_context, data = ""):
        self.OutPlaylist()


    def playlistMoveCallback(self, widget, context, x, y, selection):
        position = y // 61
        if position > len(self.player.playlist.items):
            position = len(self.player.playlist.items)
        x = self.playlist.get_children()
        if position != self.playlistPosition:
            if self.playlistPosition != -1:
                x[self.playlistPosition * 2].modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("grey"))
            x[position * 2].modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("red")) 
            self.playlistPosition = position

    def OutPlaylist(self):    
        if self.playlistPosition != -1:
            x = self.playlist.get_children()
            x[self.playlistPosition * 2].modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("grey"))
            self.playlistPosition = -1

    def deleteReceiveCallback(self, widget, context, x, y, selection, targetType, time):
        if self.dragDelete:
            self.deleteFromPlaylist(self.dragSongID)


    def playlistCall(self, widget, data = None, playlistItem = None):
        if data.button == 3:
            menu=gtk.Menu()

            menu_items = gtk.MenuItem("Play whole album (%s)" % playlistItem["albID"])
            menu_items.connect("button_press_event", self.menuitemSelect, "playalbumid:%s" % playlistItem["albID"])
            menu.append(menu_items)

            menu_items = gtk.MenuItem("Show album")
            menu_items.connect("button_press_event", self.menuitemSelect, "showalbumid:%s" % playlistItem["albID"])
            menu.append(menu_items)
            if self.admin_mode:
                menu_items = gtk.MenuItem("Delete")
                menu_items.connect("button_press_event", self.menuitemSelect, "removeplaylistsong:%s" % playlistItem["songID"])
                menu.append(menu_items)

                menu_items = gtk.MenuItem("Delete All")
                menu_items.connect("button_press_event", self.menuitemSelect, "removeallplaylist:")
                menu.append(menu_items)

            menu.show_all()
            menu.popup(None, None, None, data.button, data.time)


    def deleteFromPlaylist(self, index):
        self.player.delete_item_by_position(int(index) - 1)


    def fill_playlist(self):
        # clear out the playlist and fill

        self.playlist.destroy()
        self.playlist = gtk.VBox()
        self.playlist.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
                                             gtk.DEST_DEFAULT_HIGHLIGHT |
                                             gtk.DEST_DEFAULT_DROP,
                                             [ ( "image/x-xpixmap", 0, 81 )], gtk.gdk.ACTION_MOVE)
        self.playlist.connect("drag_data_received", self.playlistReceiveCallback)
        self.playlist.connect("drag_motion", self.playlistMoveCallback)

        i = 1
        for playlist_item in self.player.playlist.items:
                eb = gtk.EventBox() 
                self.playlist.pack_start(eb, expand = False)
                hb = gtk.HBox()
                label = gtk.Label(i)
                label.set_width_chars(3)
                hb.pack_start(label, expand = False)
                # track info 
                item = gtk.Table(1, 3)
                label = gtk.Label("<small><small><b>" + self.html_encode(playlist_item.song_title) + "</b></small></small>")
                label.set_use_markup(True)
                label.set_width_chars(15)
                item.attach(label, 0, 1, 0, 1)
                # artist/album info
                label = gtk.Label("<small><small>" + self.html_encode(playlist_item.artist_name) + "</small></small>")
                label.set_use_markup(True)
                label.set_width_chars(15)
                item.attach(label,0, 1, 1, 2)
                label = gtk.Label("<small><small><i>" + self.html_encode(playlist_item.album_name) + "</i></small></small>")
                label.set_use_markup(True)
                label.set_width_chars(15)
                item.attach(label,0, 1, 2, 3)            
                hb.pack_start(item)
                # art
                img = gtk.Image()
                self.setAlbumArt(img, playlist_item.album_has_art, playlist_item.album_id, 50)
                hb.pack_start(img, expand = False)

                frame = gtk.Frame()
                frame.set_border_width(1)
                eventbox = gtk.EventBox()
                hb.set_border_width(2)
                eventbox.connect("enter_notify_event", self.eventIn)
                eventbox.connect("leave_notify_event", self.eventOut)
            #    eventbox.connect("button_press_event", self.playlistCall, playlistItem)

                eventbox.add(hb)
                frame.add(eventbox)
                frame.drag_source_set(gtk.gdk.BUTTON1_MASK, [ ( "image/x-xpixmap", gtk.TARGET_SAME_WIDGET, int(playlist_item.song_id) ) ], gtk.gdk.ACTION_MOVE)
                frame.connect("drag_data_get", self.playlistSendCallback)
                frame.connect("drag_end", self.playlistDragEnd)

                self.playlist.pack_start(frame, expand = False)
                i += 1
        eb = gtk.EventBox()

        self.playlist.pack_start(eb, expand = False)
        null=gtk.Label()
        self.playlist.pack_start(null, expand = True)
        self.playlistScroller.add_with_viewport(self.playlist)
        self.playlistPosition = -1
        self.window.show_all()


    # TRACKS
    # ======================================

    def tracks_artist_name(self, artName, artID, arti, i):
        # create artist name label and attach
        frame = gtk.Frame()
        eb = gtk.EventBox()
        eb.connect("button_press_event", self.fillTracksCall, dict(artist_id = artID, order = 'track'))
        eb.connect("enter_notify_event", self.eventIn)
        eb.connect("leave_notify_event", self.eventOut)

        label = gtk.Label(artName)
        eb.add(label)
        frame.add(eb)
        label.set_width_chars(20)
        label.set_ellipsize(pango.ELLIPSIZE_END)
        #label.modify_fg(gtk.STATE_NORMAL, self.getMatchColour(MBMatch))
        frame.show_all()
        self.trackTable.attach(frame, 0, 1, arti, i)


    def setAlbumArt(self, img, albArt, AlbID, imgSize):
        # show album art
        if imgSize>0:
            sub_img_size = 20
            sub_img_border = 2
            if albArt:
                try:
                    buffer1 = gtk.gdk.pixbuf_new_from_file(os.path.join(app_path, 'art', '%s.jpeg' % AlbID)).scale_simple(int(imgSize), int(imgSize), gtk.gdk.INTERP_BILINEAR)
                except:
                    buffer1 = gtk.gdk.pixbuf_new_from_file(os.path.join(app_path, 'art', '0.jpg')).scale_simple(int(imgSize), int(imgSize), gtk.gdk.INTERP_BILINEAR)
            else:
                buffer1 = gtk.gdk.pixbuf_new_from_file(os.path.join(app_path, 'art', '0.jpg')).scale_simple(int(imgSize), int(imgSize), gtk.gdk.INTERP_BILINEAR)
                
                # WORKING OVERLAY
#            buffer1 = buffer1.add_alpha(False, chr(255), chr(255), chr(255))
#            buffer2 = gtk.gdk.pixbuf_new_from_file("%sstar_blue.png" % app_path ).scale_simple(sub_img_size, sub_img_size, gtk.gdk.INTERP_BILINEAR)
#            buffer2 = buffer2.add_alpha(True, chr(255), chr(255), chr(255))
#            buffer2.copy_area(0, 0, sub_img_size, sub_img_size, buffer1, int(imgSize) - sub_img_size - sub_img_border, sub_img_border)


            #buffer2.composite(buffer1, int(imgSize) - sub_img_size - sub_img_border, sub_img_border, sub_img_size, sub_img_size, 1, 1, 1, 1, gtk.gdk.INTERP_BILINEAR, 100)
#copy_area(src_x, src_y, width, height, dest_pixbuf, dest_x, dest_y)
#composite(dest, dest_x, dest_y, dest_width, dest_height, offset_x, offset_y, scale_x, scale_y, interp_type, overall_alpha)
            img.set_from_pixbuf(buffer1)

    def tracks_album_name(self, oldAlbName, albArt, albID, oldAlbi, i):
        # create album name label & art and attach

        img_sizes = [0, 20, 40, 60, 80, 100, 120]
        img_num = len(img_sizes)
        img_choice = i - oldAlbi - 1
        img_choice_2 = img_choice
        if img_choice >= img_num : img_choice = img_num - 1
        imgSize = img_sizes[img_choice]
        frame = gtk.Frame()
        eb = gtk.EventBox()
        eb.connect("button_press_event", self.fillTracksCall, dict(album_id = albID, order = 'track'))
        eb.connect("enter_notify_event", self.eventIn)
        eb.connect("leave_notify_event", self.eventOut)
        vb = gtk.VBox()
        eb.add(vb)
        label = gtk.Label(oldAlbName)
        label.set_width_chars(20)
        label.set_ellipsize(pango.ELLIPSIZE_END)
        label.set_justify(gtk.JUSTIFY_CENTER)
        #label.modify_fg(gtk.STATE_NORMAL, self.getMatchColour(MBMatch))
        img = gtk.Image()
        if img_choice_2 >= img_num:
            labelNull = gtk.Label()
            vb.pack_start(labelNull)
        vb.pack_start(img, expand = False)
        vb.pack_start(label, expand = False)
        if img_choice_2 > img_num:
            labelNull = gtk.Label()
            vb.pack_start(labelNull)
        frame.add(eb)
        self.setAlbumArt(img,albArt, albID, imgSize)
        frame.show_all()
        self.trackTable.attach(frame, 2, 3, oldAlbi, i)

    def menuitemSelect(self,widget,data = None, value = ""):

        field = string.lower(value[:value.find(':')])
        value = int(value[value.find(':') + 1 :])
        if field == "playalbumid":
            self.play_album(value)
        if field == "showalbumid":
            self.fillTracks(dict(album_id = value))
        if field == "removeplaylistsong":
            self.deleteFromPlaylist(value)
        if field == "removeallplaylist":
            self.deleteAllFromPlaylist()
        if field == "songid":
            self.player.add_song(value)

    def controlCall (self, widget, data = None, info = ""):
        self.actionButton(info)

    def actionButton(self, info):

        if self.currentFunction == "actionFillAlbums":
            if info == "prev" or info == "next":
                if info == "prev":
                    self.currentOffset = self.currentOffset - 32
                self.actionFillAlbums(self.currentWhere, self.currentOffset)
            else:
                if info == "show_tracks":
                    (x,y) = self.pane2.size_request()
                    self.pane2.set_position(x)
                    self.pane2.resize_children()
                if info == "show_albums":
                    self.pane2.set_position(0)
                    self.pane2.resize_children() 
                    self.actionFillAlbums(self.currentWhere, self.currentOffset - 16)
                if info == "show_both":
                    self.pane2.set_position(200)
                    self.pane2.resize_children()
                    self.actionFillAlbums(self.currentWhere, self.currentOffset - 16)

            

    def fillTracksCallCurrent(self, widget, data = None):
        self.fillTracksCall(widget, data, dict(album_id = self.currentAlbumID, order = 'track'))




    def fillTracksCall(self, widget, event = None, where = {}):
        if event.button == 1:
            self.fillTracks(where)
        
        if event.button == 3:

            menu=gtk.Menu()

            # tracks
            data = self.database.get_tracks(**where)
            if data:
                for (song, album, artist) in data:
                    album_id = album.id
                    album_name = album.name
                    menu_items = gtk.MenuItem('%s.\t%s' % (song.track, song.title))
                    menu_items.connect("button_press_event", self.menuitemSelect, "songid:%s" % song.id)
                    menu.append(menu_items)

            menu_items = gtk.MenuItem("Play whole album (%s)" % album_name)
            menu_items.connect("button_press_event", self.menuitemSelect, "playalbumid:%s" % album_id)
            menu.append(menu_items)

            menu_items = gtk.MenuItem("Show album")
            menu_items.connect("button_press_event", self.menuitemSelect, "showalbumid:%s" % album_id)
            menu.append(menu_items)

        #    submenu=gtk.Menu()

        #    menu_items = gtk.MenuItem("Play whole album (%s)" % value)
        #    menu_items.connect("button_press_event", self.menuitemSelect, "playalbumid:" + value)
        #    submenu.append(menu_items)

        #    menu_items = gtk.MenuItem("Show album")
        #    menu_items.connect("button_press_event", self.menuitemSelect, "showalbumid:" + value)
        #    submenu.append(menu_items)

        #    menu_items = gtk.MenuItem("Stuff")
        #    menu_items.set_submenu(submenu)
        #    menu.append(menu_items)

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)
        return True


    def fillTracks(self, where):
        self.actionFillTracks(**where)

    def actionFillTracks(self, **kw):
        # creates the tracks listing
        data = self.database.get_tracks(limit = 50, **kw)
        self.trackHolder.destroy()
        self.trackTable.destroy()
        self.trackHolder = gtk.VBox()
        self.trackTable = gtk.Table()
        self.trackTable.resize(len(data) ,3)
        i = 0
        total_i = len(data)
        (oldArtID, oldArtName, oldArti) = (0, "", 0)
        (oldAlbID, oldAlbName, oldAlbi) = (0, "", 0)

        for (song, album, artist) in data:
            # track number
            frame = gtk.Frame()
            eb = gtk.EventBox()
            eb.set_events(gtk.gdk.BUTTON_PRESS_MASK)
            eb.connect("button_press_event", self.play_song_callback ,song.id)
            eb.connect("enter_notify_event", self.eventIn)
            eb.connect("leave_notify_event", self.eventOut)
            label = gtk.Label(str(song.track) + ".")
            label.set_width_chars(3)
            hb = gtk.HBox()
            hb.pack_start(label, expand = False)

            eb.drag_source_set(gtk.gdk.BUTTON1_MASK, [ ( "image/x-xpixmap", gtk.TARGET_SAME_WIDGET, int(song.id) ) ], gtk.gdk.ACTION_MOVE)
            eb.connect("drag_data_get", self.tracklistSendCallback)
            eb.connect("drag_end", self.tracklistDragEnd)

            eb.set_events(gtk.gdk._2BUTTON_PRESS)

            label = gtk.Label(song.title)
            label.set_width_chars(30)
            label.set_ellipsize(pango.ELLIPSIZE_END)
        #    label.modify_fg(gtk.STATE_NORMAL, self.getMatchColour(songMBMatch))
        #    if fileType == "F":
        #        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))

            hb.pack_start(label)
            eb.add(hb)
            frame.add(eb)
            frame.show_all()
            self.trackTable.attach(frame, 1, 2, i, i+1)

            # artist name
            if oldArtID != artist.id:
                if i != 0:
                    self.tracks_artist_name(oldArtName, oldArtID, oldArti, i)
                (oldArti, oldArtID, oldArtName) = (i, artist.id, artist.name)
            # album name & art
            if oldAlbID != album.id:
                if i != 0:
                    self.tracks_album_name(oldAlbName, oldAlbArt, oldAlbID, oldAlbi, i)
                (oldAlbi, oldAlbID, oldAlbName, oldAlbArt) = (i, album.id, album.name, album.art)
            i += 1
        if i != 0:
            # artist name
            if oldArti != i:
                self.tracks_artist_name(oldArtName, oldArtID, oldArti, i)
            # album name & art
            if oldAlbi != i:
                self.tracks_album_name(oldAlbName, oldAlbArt, oldAlbID, oldAlbi, i)

        self.trackHolder.pack_start(self.trackTable, expand = False)
        label = gtk.Label()
        label.set_size_request(0, 0)
        self.trackHolder.pack_start(label, expand = True)

        self.trackScroller.add_with_viewport(self.trackHolder)
        self.trackHolder.show_all()
        #resize
        if self.pane2.get_position() <= 200:
            if self.pane2.get_position() < (i*21)+4:
                x=(i*21)+4
                if x>200: x=200
                self.pane2.set_position(x)
        self.trackScroller.get_vadjustment().set_value(0)


    # ALBUMS
    # ======================================

    def fillAlbumsCall(self, widget, data = None, where = None):
        text_size = 25
        self.fillAlbums(where)
        # scroll the artist list too
        position = self.database.get_artists(count = True, tracks = int(self.artistCombo.get_active_text()), letter = where)
        adjustment = self.artistScroller.get_vadjustment()

        if position * text_size < adjustment.upper - adjustment.page_size:
            adjustment.set_value(position * text_size)
        else:
            adjustment.set_value(adjustment.upper - adjustment.page_size)
        self.artistScroller.set_vadjustment(adjustment)

    def fillAlbums(self, position):
        self.actionFillAlbums(position)


    def actionFillAlbums(self, position, offset = 0):
        # get and display album info
        img_size = 160
        table_width = 4
        table_height = 4
        table_size = table_width * table_height

        adjustment=self.albumScroller.get_vadjustment()
        img_size = (adjustment.page_size // table_height) - 50
        # skip to albums starting with ...
        if position:
            offset = self.database.get_albums_with_artist(letter = position, count = True)

        totalAlbums = self.database.get_albums_with_artist(count = True)        

        if offset < 0:
            offset = totalAlbums + offset
        # get the album info
        data = self.database.get_albums_with_artist(offset = offset, limit = table_size)

        if offset + table_size <= totalAlbums:
            self.currentOffset = offset + table_size
        self.currentFunction = "actionFillAlbums"
        # have we wrapped round the end of the albums?
        needed = table_size - len(data)
        if needed:
            data.extend(self.database.get_albums_with_artist(offset = 0, limit = needed))
            self.currentOffset = needed

        self.albumTable.destroy()
        self.albumTable = gtk.Table(table_width, table_height)
        self.albumTable.set_row_spacings(5)
        self.tooltips = gtk.Tooltips()
        i = 0
        for album, artist in data:
            eb = gtk.EventBox()
            eb.set_border_width(1)
            
            eb2 = gtk.EventBox()
            eb2.set_border_width(1)
            frame = gtk.Frame()
            eb2.connect("button_press_event", self.fillTracksCall, dict(album_id = album.id, order = 'track'))
            eb2.connect("enter_notify_event", self.eventIn)
            eb2.connect("leave_notify_event", self.eventOut)
            vb = gtk.VBox()
            vb.set_size_request(164, -1) #164
            vb.set_border_width(2)
            table = gtk.Table(1, 2)
            img = gtk.Image()
            self.setAlbumArt(img, album.art, album.id, img_size) #160

            label=gtk.Label()
            label.set_max_width_chars(11)
            label.set_ellipsize(pango.ELLIPSIZE_END)
            label.set_justify(gtk.JUSTIFY_CENTER)
            label=gtk.Label("<b>" + self.html_encode(artist.name) + "</b>")
            
            label.set_use_markup(True)
            #label.modify_fg(gtk.STATE_NORMAL, self.getMatchColour(artMBMatch))
            eventbox = gtk.EventBox()
            eventbox.add(label)
            self.tooltips.set_tip(eventbox, artist.name)
            vb.pack_start(img,expand=False)
            vb.pack_start(eventbox,expand=False)
            
            label=gtk.Label(album.name)
            label.set_max_width_chars(11)
            label.set_ellipsize(pango.ELLIPSIZE_END)
            label.set_justify(gtk.JUSTIFY_CENTER)
        #    label.modify_fg(gtk.STATE_NORMAL, self.getMatchColour(albMBMatch))
        #    if albumFileType=="F":
        #        label.modify_fg(gtk.STATE_NORMAL,gtk.gdk.color_parse("red"))
            eventbox = gtk.EventBox()
            eventbox.add(label)
            self.tooltips.set_tip(eventbox, album.name)
            vb.pack_start(eventbox, expand=False)
            
            frame.add(vb)
            eb2.add(frame)
            eb.add(eb2)
            self.albumTable.attach(eb, i % table_width, (i % table_width) + 1, i // table_width, (i // table_width) + 1)
            i += 1
        
        self.albumScroller.get_vadjustment().set_value(0)
        self.albumScroller.add_with_viewport(self.albumTable)

    #    self.pane2.set_position(0)
        self.window.show_all()
        # stop refresh from status
        self.panesize = self.pane2.get_position()
        self.pane_timer = 0

    def showAlbums(self, widget, data=None):
        self.pane2.set_position(0)
        return True


    def makeAlpha(self,title, where):
        button=gtk.Button(title)
        button.set_focus_on_click(False)
        button.connect("button_press_event", self.fillAlbumsCall, where)
        return button



    def makeControl_old(self,title, info):
        frame=gtk.Frame()
        label=gtk.Label(title)
        eb=gtk.EventBox()
        eb.connect("button_press_event", self.controlCall, info)
        eb.connect("enter_notify_event", self.eventIn)
        eb.connect("leave_notify_event", self.eventOut)
        eb.add(frame)
        frame.add(label)
        return eb

    def makeControl(self,title, info):
        button=gtk.Button(title)
        button.connect("button_press_event", self.controlCall, info)
        return button

    # INIT
    # ======================================


    def searchPress(self, widget, data=None):
        txt=self.searchbox.get_text()
        self.fillTracks(dict(search = txt))


    def eventKeyPress(self, widget, data=None):
        if data.keyval==65470:
            self.helpAbout()
        elif data.keyval==65361:
            # left
            self.actionButton('prev')
        elif data.keyval==65363:
            # right
            self.actionButton('next')
        elif data.keyval<255:
            if data.state & gtk.gdk.CONTROL_MASK:
                if not self.admin_mode:
                    # see if we have gone to admin mode
                    self.keylogger += string.lower(chr(data.keyval))
                    if len(self.keylogger)>10:
                        self.keylogger=self.keylogger[-10:]
                    self.checkAdmin()
                else:

                        
                    key = string.lower(chr(data.keyval))
                    if key == 'q':
                        self.admin_mode = False
                        self.msgWindow("Admin mode disabled")
                    elif key == '/':
                        self.msgWindow("Admin mode")
                    elif key == 'b':
                        self.bonus_track = True
                        self.msgWindow("Bonus track")
                    elif key == 's':
                        self.player.play_next()
                     #   self.msgWindow("Skip")
                    elif key == 'f':                
                        self.fullscreen_mode = not self.fullscreen_mode
                        if self.fullscreen_mode:
                            self.window.fullscreen()
                        else:
                            self.window.unfullscreen()
                    elif key == 'l':                
                        self.limit_songs_mode = not self.limit_songs_mode
                        if self.limit_songs_mode:
                            self.msgWindow("limit of %s songs on" % self.limit_songs_number)
                        else:
                            self.msgWindow("limit off")
                    elif key == 'c':                
                        if self.limit_songs_mode:
                            self.playlistArray = self.playlistArray[:self.limit_songs_number + 1]
                            self.refreshPlaylist()
                    elif key == 'n':
                        try:
                            value = int(self.keylogger[-2:])
                            self.limit_songs_number = value
                            self.msgWindow("new limit of %s songs" % self.limit_songs_number)
                        except:
                            try:
                                value = int(self.keylogger[-1:])
                                self.limit_songs_number = value
                                self.msgWindow("new limit of %s songs" % self.limit_songs_number)
                            except:
                                pass

                    elif key == 'd':
                        try:
                            value = int(self.keylogger[-2:])

                        except:
                            try:
                                value = int(self.keylogger[-1:])
                            except:
                                value = 0
                        if value:
                            try:
                                self.deleteFromPlaylist(value)
                            except:
                                pass
                    self.keylogger += key
                    if len(self.keylogger)>10:
                        self.keylogger=self.keylogger[-10:]
                        
                                                    
    def pane2_resize_callback(self, widget, data=None):
        print "!!!!! moo"
        #self.fillAlbums(0)


    def checkAdmin(self):
        if self.keylogger[-len(self.admin_password):]==self.admin_password:
            self.admin_mode = True
            self.msgWindow("Admin mode enabled")

    def helpAbout(self):
        dialog = gtk.Dialog()
        ok_button = dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        ok_button.set_alignment(0,0)
        label = gtk.Label("<big><b>Jukebox " + version + "</b></big>")
        label.set_use_markup(True)
        dialog.vbox.pack_start(label)
        label = gtk.Label("\nWritten by Toby Dacre\n\n\nHAPPY BIRTHDAY ANA :)\n\n")
        dialog.vbox.pack_start(label)    
        dialog.set_has_separator(False)
        dialog.show_all()
        dialog.run()
        dialog.destroy()


    def msgWindow(self, msg):
        if not self.msg_window_active:
            self.msg_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.msg_window.set_border_width(2)
            self.msg_window.set_position(gtk.WIN_POS_CENTER)
            self.msg_window.set_default_size(200, 50)
            self.msg_window.modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("red"))
            eb=gtk.EventBox()
            eb.modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("yellow"))
            self.msg_label=gtk.Label(msg)
            eb.add(self.msg_label)
            self.msg_window.add(eb)
            self.msg_window.set_decorated(False)
            self.msg_window.set_keep_above(True)
            self.msg_window.show_all()
            self.msg_window_active=True
            gobject.timeout_add(2000, self.msgWindowClose)

    def msgWindowClose(self):
        self.msg_window.destroy()
        self.msg_window_active=False

    def statusTimeClick(self, widgit, data=None):
        self.statusTimeToggle = not self.statusTimeToggle


    def __init__(self):

        self.database = player.Database()

        self.panesize = 0
        self.pane_timer = 0
        #style
    #    gtk.rc_parse("/home/toby/scripts/dark.rc")
            # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("JukeBox "+ version)
        self.window.set_border_width(10)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("delete_event", self.delete_event)
        self.window.set_default_size(400, 800)
        self.window.connect("key_press_event", self.eventKeyPress)
        #self.window.fullscreen()
        
        # artist list
        self.artistHolder=gtk.VBox()
        self.artistHolder.set_spacing(0)
        # options dropdown
        hb=gtk.HBox()
        label=gtk.Label("Artists with")
        hb.pack_start(label,expand=False,padding=1)

        self.artistCombo = gtk.combo_box_new_text()
        for item in [1, 2, 3, 5, 7, 9, 10, 25, 50, 75, 100]:
            self.artistCombo.append_text(str(item))
        self.artistCombo.set_active(6)
        self.artistCombo.connect("changed", self.eventChange)
        hb.pack_start(self.artistCombo,expand=False,padding=1)
        label=gtk.Label("songs")
        hb.pack_start(label,expand=False,padding=1)
        self.artistHolder.pack_start(hb,expand=False,padding=6)

        # artist list area
        self.artistList=gtk.ListStore(str,int)
        self.artistSubHolder=gtk.TreeView(self.artistList)
        self.artistSubHolder.connect("button_press_event", self.eventPress,7)
        self.tvcolumn = gtk.TreeViewColumn()
        self.artistSubHolder.set_headers_visible(False)
        self.artistSubHolder.append_column(self.tvcolumn)
        self.cell = gtk.CellRendererText()
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn.add_attribute(self.cell, 'text', 0)
        self.artistSubHolder.set_hover_selection(gtk.SELECTION_BROWSE)
        self.artistScroller = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.artistScroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.artistScroller.set_size_request(150, -1)
        self.artistScroller.add_with_viewport(self.artistSubHolder)
        # fill artists list
        self.fillArtists(10)
        self.artistHolder.pack_start(self.artistScroller)

        # tracks area
        self.trackTable=gtk.Table()
        self.trackTable.set_border_width(2)
        self.trackHolder = gtk.VBox()
        self.trackHolder.pack_start(self.trackTable)
        label = gtk.Label()
        self.trackHolder.pack_start(label, expand = True)
        self.trackScroller = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.trackScroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.trackScroller.add_with_viewport(self.trackHolder)

        # albums area
        self.albumTable=gtk.Table()
        self.albumScroller = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.albumScroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.albumScroller.add_with_viewport(self.albumTable)
        #self.albumScrollerEventBox = gtk.EventBox()
        #self.albumScrollerEventBox.add(self.albumScroller)
        #self.albumScrollerEventBox.connect("configure-event", self.pane2_resize_callback)



    #    self.albumScroller.set_resize_mode(gtk.RESIZE_IMMEDIATE)
    #    self.albumScroller.connect("configure-event", self.pane2_resize_callback)

        # status area
        self.statusArea=gtk.VBox(spacing=10)
        self.statusArea.set_size_request(250,-1)
        self.statusTop=gtk.HBox()
        # currently playing
        self.StatusTopLeft=gtk.VBox(spacing=5)
        self.statusArtist=gtk.Label("artist")
        self.statusAlbum=gtk.Label("album")
        self.statusTrack=gtk.Label("track")
        self.statusArt=gtk.Image()
        self.statusArt.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
                                             gtk.DEST_DEFAULT_HIGHLIGHT |
                                             gtk.DEST_DEFAULT_DROP,
                                             [ ( "image/x-xpixmap", 0, 81 )], gtk.gdk.ACTION_MOVE)
        self.statusArt.connect("drag_data_received", self.currentReceiveCallback)
        self.statusArtEb=gtk.EventBox()
        self.statusArtEb.connect("button_press_event", self.fillTracksCallCurrent)
        self.statusArtEb.add(self.statusArt)
        self.StatusTopLeft.pack_start(self.statusArtist,expand=False)
        self.StatusTopLeft.pack_start(self.statusAlbum,expand=False)
        self.StatusTopLeft.pack_start(self.statusArtEb,expand=False)
        self.StatusTopLeft.pack_start(self.statusTrack,expand=False)
        # volume
        self.StatusTopRight=gtk.VBox()
#        self.ctlMute=gtk.Button("mute")
#        self.ctlMute.connect("button_press_event", self.butMute)
#        self.StatusTopRight.pack_start(self.ctlMute,expand=False)

        self.ctlVol=gtk.VScale()
        self.ctlVol.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.ctlVol.set_range(0,100)
        self.ctlVol.set_inverted(True)
        self.ctlVol.connect("value-changed", self.volumeChange)
        self.ctlVol.set_draw_value(False)
        
        self.StatusTopRight.pack_start(self.ctlVol)

        self.statusTop.pack_start(self.StatusTopLeft)
        self.statusTop.pack_start(self.StatusTopRight,expand=False)
        self.statusArea.pack_start(self.statusTop,expand=False)

        # time left indicator
        self.statusTime=gtk.HBox()
        self.statusTimeEventBox=gtk.EventBox()
        self.statusTimeLabel=gtk.Label()
        self.statusTimeLabel.set_width_chars(5)
        self.statusTimeEventBox.add(self.statusTimeLabel)
        self.statusTimeEventBox.connect("button_press_event", self.statusTimeClick)
        self.statusProgress=gtk.ProgressBar()
        self.statusProgress.set_size_request(150, 3)
        self.statusTime.pack_start(self.statusProgress)
        self.statusTime.pack_start(self.statusTimeEventBox)
        self.statusArea.pack_start(self.statusTime,expand=False)

        # buttons
        self.ButtonBox=gtk.HBox()
#        button=gtk.Button("Play")
#        button.connect("button_press_event", self.butPlay)
#        self.ButtonBox.pack_start(button,expand=False)
#    #    button=gtk.Button("prev")
#    #    button.connect("button_press_event", self.butPrev)
#    #    self.ButtonBox.pack_start(button,expand=False)
#        button=gtk.Button("next")
#        button.connect("button_press_event", self.butNext)
#        self.ButtonBox.pack_start(button,expand=False)
#        button=gtk.Button("Stop")
#        button.connect("button_press_event", self.butStop)
#        self.ButtonBox.pack_start(button,expand=False)

        null=gtk.Label()
        self.ButtonBox.pack_start(null)
        
#        button=gtk.Button("FS")
#        button.connect("button_press_event", self.butFullScreen)
#        self.ButtonBox.pack_start(button,expand=False)


#        null=gtk.Label()
#        self.ButtonBox.pack_start(null)

#        img=gtk.Image()
#        img.set_from_icon_name("gtk-delete",gtk.ICON_SIZE_BUTTON)
#        img.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
#                                             gtk.DEST_DEFAULT_HIGHLIGHT |
#                                             gtk.DEST_DEFAULT_DROP,
#                                             [ ( "image/x-xpixmap", 0, 81 )], gtk.gdk.ACTION_MOVE)
#        img.connect("drag_data_received", self.deleteReceiveCallback)
#        self.ButtonBox.pack_start(img,expand=False)
#        self.statusArea.pack_start(self.ButtonBox,expand=False)

        # playlist 

        self.playlist = gtk.VBox()
        self.playlistScroller = gtk.ScrolledWindow(hadjustment = None, vadjustment = None)
        self.playlistScroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.playlistScroller.set_size_request(250, -1)
        self.playlistScroller.add_with_viewport(self.playlist)

        self.statusArea.pack_start(self.playlistScroller)


        # alpha bar
        alphabar = gtk.VBox()
        alphabar.pack_start(self.makeAlpha(" # ", "#"), expand=False)
        for i in range(26):
            alphabar.pack_start(self.makeAlpha(chr(i+65), chr(i+65) ), expand=False)
        alphabar.pack_start(self.makeAlpha("?", "~"), expand=False)

        # albumNav
        albumNav = gtk.HBox()
        albumNav.pack_start(self.makeControl("tracks", "show_tracks"))
        albumNav.pack_start(self.makeControl("albums", "show_albums"))
        albumNav.pack_start(self.makeControl("both", "show_both"))
        albumNav.pack_start(self.makeControl("<--", "prev"))
        albumNav.pack_start(self.makeControl("-->", "next"))

        # search status etc
        self.mainSuperHolder = gtk.VBox()
        self.mainStatus = gtk.HBox()
        label = gtk.Label("Search")
        self.mainStatus.pack_start(label, expand = False, padding = 6)
        self.searchbox = gtk.Entry()
        self.searchbox.connect("changed", self.searchPress)
        self.mainStatus.pack_start(self.searchbox, expand = False, padding = 6)
        self.updateProgress = gtk.ProgressBar()
        self.updateProgress.set_size_request(150, 3)
        self.mainStatus.pack_start(self.updateProgress, expand = False, padding = 6)

        self.mainSuperHolder.pack_start(self.mainStatus, expand = False)

        self.mainWindow = gtk.HBox()
        
        self.mainHolder2 = gtk.VBox()
        self.mainHolder = gtk.HBox()
        self.mainHolder.pack_start(alphabar, expand = False)

        self.pane2 = gtk.VPaned()
        self.pane2.set_position(0)
        self.pane2.pack1(self.trackScroller)
        self.pane2.pack2(self.albumScroller)
        self.pane2EventBox = gtk.EventBox()
        self.pane2EventBox.add(self.pane2)
        self.pane2.set_events(gtk.gdk.CONFIGURE)
        self.pane2.connect("configure_event", self.pane2_resize_callback)
        self.mainHolder.pack_start(self.pane2EventBox)
        self.mainHolder2.pack_start(self.mainHolder)
        self.mainHolder2.pack_start(albumNav, expand = False)
        self.pane1 = gtk.HPaned()
        self.pane1.pack1(self.artistHolder)
        self.pane1.pack2(self.mainHolder2)

        self.mainSuperHolder.pack_start(self.pane1)

        self.mainWindow.pack_start(self.statusArea, expand = False)
        self.mainWindow.pack_start(self.mainSuperHolder)
        self.window.add(self.mainWindow)
        self.window.show_all()

        self.fillAlbums("A")

        # player
        self.player = player.Player()    
        volume = self.player.get_volume()
        self.ctlVol.set_value(volume)

        self.player.playlist.add_trigger(self.fill_playlist)
        self.player.add_trigger_song_change(self.setCurrentTrack)
        # start monitoring thread
        self.play_thread_id = thread.start_new_thread(self.status, ())

def start():
    gobject.threads_init()
    app = jukebox()
    gtk.main()

if __name__ == "__main__":
    start()
