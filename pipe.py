#!/usr/bin/env python

from os.path import exists
from time import sleep
from threading import Thread
import gst

class Pipe(object):
    
    def __init__(self, name = None):

        self.name = name
        self.filepath = ''
        self.max_volume = 1.0
        self.poll_time = 0.01
        self.fade_in_time = 5.0
        self.fade_out_time = 5.0

        self.duration = 0
        self.stopped = True
        self.alive = True
        self.fade_thread = None

        # build the player
        self.player = gst.Pipeline("player")
        source = gst.element_factory_make("filesrc", "file-source")
        self.player.add(source)
        decoder = gst.element_factory_make("decodebin", "decoder")
        self.player.add(decoder)
        converter = gst.element_factory_make("audioconvert", "converter")
        self.player.add(converter)
        volume = gst.element_factory_make("volume", "volume")
        self.player.add(volume)
        sink = gst.element_factory_make("alsasink", "sink")
        self.player.add(sink)
        source.link(decoder)
        gst.element_link_many(converter, volume, sink)
        # Reference used in self.on_new_decoded_pad()
        self.apad = converter.get_pad('sink')
        # Connect handler for 'new-decoded-pad' signal 
        decoder.connect('new-decoded-pad', self.on_new_decoded_pad)
        #decoder.connect('unknown-type', self.on_unknown_type) #kills pipe :(

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)


    def on_new_decoded_pad(self, element, pad, last):
        caps = pad.get_caps()
        name = caps[0].get_name()
        if name == 'audio/x-raw-float' or name == 'audio/x-raw-int':
            if not self.apad.is_linked(): # Only link once
                pad.link(self.apad)


    def set_volume(self, arg):
        self.max_volume = float(arg)/100
        self.player.get_by_name("volume").set_property('volume', self.max_volume)

    def setFile(self, filename):
        self.filepath = filename
        if exists(self.filepath):
            try:
                self.player.set_state(gst.STATE_NULL)
                self.player.get_by_name("file-source").set_property('location', self.filepath)
                self.stopped = False
            except:
                self.stopped = True
        

    def start(self):
        self.player.get_by_name("volume").set_property('volume', self.max_volume)
        self.player.set_state(gst.STATE_PLAYING)
        self.stopped = False


    def stop(self):
        self.player.set_state(gst.STATE_NULL)
        self.play_thread_id = None

    def fadein(self):
       # self.play_thread_id = thread.start_new_thread(self.fade_thread, ('fadein',))
        self.clear_fade()
        self.fade_thread = FadeInThread(self)
        self.fade_thread.start()

    def fadeout(self):
       # self.play_thread_id = thread.start_new_thread(self.fade_thread, ('fadeout',))
        self.clear_fade()
        self.fade_thread = FadeOutThread(self)
        self.fade_thread.start()

    def clear_fade(self):
        # kill any current fade thread
        if self.fade_thread and self.fade_thread.is_alive():
            self.alive = False
            self.fade_thread.join()
            self.alive = True

    def exit(self):
        # kill all life
        self.clear_fade()
        self.player.set_state(gst.STATE_NULL)


    def get_state(self):
        try:
            return self.player.get_state()
        except gst.QueryError:
            return False


    def get_duration(self):
        try:
            self.stopped = False
            return self.player.query_duration(gst.FORMAT_TIME, None)[0]
        except gst.QueryError:
            self.stopped = True
            return 0

    def get_position(self):
        try:
            position = self.player.query_position(gst.FORMAT_TIME, None)[0]
            duration = self.get_duration()
            if duration and duration - position == 0:
                self.stopped = True
            return position
        except gst.QueryError:
            self.stopped = True
            return 0

    def song_ending(self):
        position = self.get_position()
        duration = self.get_duration()
        if not duration:
            return True
        time_left = duration - position
        if time_left <= 5000000000 and time_left <> 0:
            return True
        else:
            return False
        # change to and is playing FIXME 

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()

class FadeInThread(Thread):

    def __init__(self, pipe):
        Thread.__init__(self)
        self.pipe = pipe

    def run(self):
        pipe = self.pipe
        player = pipe.player
        player.set_state(gst.STATE_PLAYING)
        volume = 0.0
        change = pipe.poll_time/pipe.fade_in_time

        while pipe.alive:
            player.get_by_name("volume").set_property('volume', volume)
            volume = volume + change
            if volume >= pipe.max_volume:
                player.get_by_name("volume").set_property('volume', pipe.max_volume)
                break
            sleep(pipe.poll_time)

class FadeOutThread(Thread):

    def __init__(self, pipe):
        Thread.__init__(self)
        self.pipe = pipe

    def run(self):
        pipe = self.pipe
        player = pipe.player
        volume = pipe.max_volume
        change = -pipe.poll_time/pipe.fade_out_time

        while pipe.alive:
            player.get_by_name("volume").set_property('volume', volume)
            volume = volume + change
            if volume <= 0.0:
                player.get_by_name("volume").set_property('volume', 0.0)
                player.set_state(gst.STATE_NULL)
                break                    
            sleep(pipe.poll_time)
