import os
import os.path
import sys
import mimetypes
import re

from PIL import Image

from schema import *


def utf(arg):
    # utf-8 decoding removing any unknown chars
    try:
        out = arg.decode('utf-8')
        return out
    except UnicodeDecodeError:
        # we got a decode error try each char in turn
        out = []
        for char in arg:
            try:
                convert = char.decode('utf-8')
                out.append(convert)
            except UnicodeDecodeError:
                out.append('_')
        return ''.join(out)



def find_songs(path, quick = False):
    """search path for music files and add to database"""

    num_dirs = 0
    for x in os.walk(path):
        num_dirs +=1

    processed_dirs = 0
    out = ''
    for root, dirs, files in os.walk(path):
        if not files:
            continue
        (head, album) = os.path.split(root)
        (head, artist) = os.path.split(head)
        # force to unicode
        album = utf(album)
        artist = utf(artist)
        path = utf(root)
        dir_data = dict(path = path, artist = artist, album = album, songs = [], pattern = None)
        for file in files:
            file_path = os.path.join(root, file)
            (mimetype, junk) = mimetypes.guess_type(file_path, True)
            # music files
            if mimetype and mimetype.startswith('audio/') and mimetype[6:8] != 'x-':
                (title, junk) = os.path.splitext(file)
                # force to unicode
                file_path = utf(file_path)
                title = utf(title)

                data = dict(mimetype = mimetype,
                            file_path = file_path,
                            title = title)
                dir_data['songs'].append(data)
            # artwork
            elif mimetype and mimetype.startswith('image/'):
                dir_data['art'] = file_path
        if dir_data['songs']:
            add_songs(dir_data, quick)

        processed_dirs += 1
        sys.stdout.write(chr(8) * len(out))
        out = '%s of %s' % (processed_dirs, num_dirs)
        sys.stdout.write(out)
        sys.stdout.flush()



artist_cache = {}

def is_various_artists(artist):

    if not artist or artist.lower() in ['various', 'various artists']:
        return True
    else:
        return False


def get_artist_id(session, artist):
    """get id for artist adding to database if not already there"""

    if is_various_artists(artist):
        return None

    # check cache
    if artist in artist_cache:
        return artist_cache[artist]

    # check database
    try:
        data = session.query(Artist).filter_by(name = artist).one()
        artist_cache[artist] = data.id
        return data.id
    except sa.orm.exc.NoResultFound:
        # not found so add
        obj = Artist(artist, False)
        session.add(obj)
        session.flush()
        artist_cache[artist] = obj.id
        return obj.id


def get_album_id(session, dir_data, artist_id):
    """get the id of the album adding to database if needed"""

    path = dir_data['path']

    try:
        data = session.query(Album).filter_by(path = path).one()
        return (False, data.id)
    except sa.orm.exc.NoResultFound:
        # not found so add
        album = dir_data['album']
        artist = dir_data['artist']
        pattern = dir_data['pattern']
        if is_various_artists(artist):
            sort = '~'
        else:
            sort = artist[0].upper()
        obj = Album(path, album, artist_id, False, sort, pattern)
        session.add(obj)
        session.flush()
        id = obj.id
     #   print 'added %s - %s' % (dir_data['artist'], dir_data['album'])
        return (True, id)


def add_song(session, path, track, title, artist_id, album_id, mimetype, unknown, pattern):
    """add song to the database if not there"""
    try:
        data = session.query(Song).filter_by(path = path).one()
    except sa.orm.exc.NoResultFound:
        # not found so add
        obj = Song(path, track, title, artist_id, album_id, mimetype, unknown, pattern)
        session.add(obj)



def add_songs(dir_data, quick):
    """add songs to the database"""

    session = Session()
    session.begin()
    artist_id = get_artist_id(session, dir_data['artist'])
    new_album, album_id = get_album_id(session, dir_data, artist_id)
    if quick and new_album:
        return

    analyse_songs(dir_data)

    # album art
    if 'art' in dir_data:
        path = dir_data['art']
        # make thumbnail
        try:
            image = Image.open(path)
            image.thumbnail((300,300), Image.ANTIALIAS)
            image.save(os.path.join("art/", '%s.jpeg' % album_id), "JPEG")
            data = session.query(Album).filter_by(id = album_id).one()
            data.art = True
        except IOError:
            pass
       # session.save(data)

    for song in dir_data['songs']:
        artist = song['artist'] or dir_data['artist']
        artist_id = get_artist_id(session, artist )

        track = song['track']
        title = song['title'] or 'untitled'
        mimetype = song['mimetype']
        path = song['file_path']
        unknown = not song['title']
        pattern = song['pattern']

        add_song(session, path, track, title, artist_id, album_id, mimetype, unknown, pattern)

    session.commit()
    session.close()


def analyse_songs(dir_data):
    """attempt to get track no, artist, title from filenames"""

    # build our regular expessions
    r_trackno = r'\s*(?P<track>\d{1,3})[\s_.-]+'
    r_various = r'(?i)[.-]*\s*(various artists|various)\s*[.-]*\s*'
    
    regs = []
    # 1 Numbered Artist Included
    r = r'^%s%s\s*[.-]*\s*(?P<title>\S.+)' % (r_trackno , dir_data['artist'])
    regs.append([re.compile(r), '# <artist> - title'])
    # 2 Numbered Various Artist Included
    r =  r'^%s%s\s*(?P<artist>\S.+?)\s*-\s*(?P<title>\S.+)\s*' % (r_trackno, r_various)
    regs.append([re.compile(r), '# <various> artist - title'])
    # 4 Numbered Artist Track
    r = r'^%s\s*(?P<artist>\S.+?)\s*-\s*(?P<title>\S.+)\s*' % r_trackno
    regs.append([re.compile(r), '# artist - title'])
    # 5 Numbered Artist Plus Included
    r = r'^%s%s\s*-\s*(?P<artist>\S.+?)\s*-\s*(?P<title>\S.+)\s*' % (r_trackno , dir_data['artist'])
    regs.append([re.compile(r), '# <artist> - artist - title'])
    # 3 Numbered Basic
    r = r'^%s(?P<title>.+)' % r_trackno
    regs.append([re.compile(r), '# title'])
    
    counts = []
    num_regs = len(regs)
    for i in range(num_regs):
        counts.append(0)

    num_songs = len(dir_data['songs'])

    for song in dir_data['songs']:
        title = song['title']
        # try each regex and see which match
        for i in range(num_regs):
            if regs[i][0].search(title):
                counts[i] += 1

    # which was the most effective regex?
    max = 0
    best_reg = None
    for i in range(num_regs):
        if counts[i] > max:
            max = counts[i]
            best_reg = i

    if best_reg == None:
        print '\nUnknown track format', dir_data['path']
        return False
    
    dir_data['pattern'] = regs[best_reg][1]

    for song in dir_data['songs']:
        match = regs[best_reg][0].search(song['title'])
        if match:
            try:
                track = match.group('track')
            except IndexError:
                track = None
            try:
                artist = match.group('artist')
            except IndexError:
                artist = None
            try:
                title = match.group('title')
            except IndexError:
                title = None
            pattern = regs[best_reg][1]
        else:
            # we know nothing
            track = None
            artist = None
            title = None
            pattern = None

        song['track'] = track
        song['title'] = title
        song['artist'] = artist
        song['pattern'] = pattern
    return True




print '~' * 20

def check_albums():

    session = Session()
    albums = session.query(Album).all()
    session.begin()
    for album in albums:
        path = album.path
        if not os.path.isdir(path):
            print 'missing %s' % path
            session.delete(album)
    session.commit()
    session.close()


#check_albums()
find_songs('/stuff2/archive/music/Albums/')



