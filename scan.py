import time

from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3

from schema import *


def scan_tag(player, pause = None):
    session = Session()
    prescanned = session.query(Scan.song_id).filter(Scan.scan == 'tag').subquery()
    tracks = session.query(Song).outerjoin((prescanned, Song.id == prescanned.c.song_id)).filter(prescanned.c.song_id == None).all()
    session.close()

    for song in tracks:
        if not player.alive:
            break
        path = song.path
        info = {}
        session = Session()
        session.begin()
        try:
            if song.mimetype == "audio/mpeg":
                tagobj = EasyID3(path)
                fileobj = MP3(path)
                info['bitrate'] = int(fileobj.info.bitrate)
            elif song.mimetype == "audio/flac":
                tagobj = FLAC(path)
                fileobj = tagobj
            else:
                print 'unknown mimetype', song.mimetype
                continue

            try:
                info['title'] = tagobj['title'][0]
            except:
                pass

            try:
                info['year'] = tagobj['date'][0]
            except:
                pass

            try:
                info['track'] = tagobj['tracknumber'][0]
            except:
                pass

            try:
                length = int(fileobj.info.length)
            except:
                length = None

            try:
                info['album'] = tagobj['album'][0]
            except:
                pass

            try:
                info['artist'] = tagobj['artist'][0]
            except:
                pass

            # update
            if length:
                song.length = length
                session.add(song)

            if info:
                for key in info.iterkeys():
                    tag = Tag(song.id, key, info[key])
                    session.add(tag)
            success = True
        except:
            success = False

        scan = Scan(song.id, 'tag', success)
        session.add(scan)
        session.commit()
        session.close()

        if pause:
            time.sleep(pause)


