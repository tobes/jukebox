
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, relation
from sqlalchemy.ext.declarative import declarative_base
import datetime



# database setup
Base = declarative_base()


# define the tables
class Song(Base):
    __tablename__ = 'song'

    id = sa.Column(sa.Integer, primary_key=True)
    path = sa.Column(sa.Unicode(assert_unicode = False))
    title = sa.Column(sa.Unicode(assert_unicode = False))
    unknown = sa.Column(sa.Boolean)
    track = sa.Column(sa.Integer)
    length = sa.Column(sa.Integer)
    unknown = sa.Column(sa.Boolean)
    mimetype = sa.Column(sa.Unicode(assert_unicode = False))
    album_id = sa.Column(sa.Integer, sa.ForeignKey('album.id'))
    artist_id = sa.Column(sa.Integer, sa.ForeignKey('artist.id'))
    pattern = sa.Column(sa.Text)


    def __init__(self, path, track, title, artist_id, album_id, mimetype, unknown, pattern):
        self.path = path
        self.track = track
        self.title = title
        self.artist_id = artist_id
        self.album_id = album_id
        self.mimetype = mimetype
        self.unknown = unknown
        self.pattern = pattern


    def __repr__(self):
       return "<Song %s `%s`>" % (self.id, self.title)

class Artist(Base):
    __tablename__ = 'artist'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode(assert_unicode = False))
    unknown = sa.Column(sa.Boolean)

    artist_id = relation("Song", backref="song_artist", cascade="all, delete")
    album_id = relation("Album", backref="album_artist", cascade="all, delete")


    def __init__(self, name, unknown):
        self.name = name
        self.unknown = unknown

    def __repr__(self):
       return "<Artist %s>" % self.name

class Album(Base):
    __tablename__ = 'album'

    id = sa.Column(sa.Integer, primary_key=True)
    path = sa.Column(sa.Unicode(assert_unicode = False))
    name = sa.Column(sa.Unicode(assert_unicode = False))
    art = sa.Column(sa.Boolean)
    unknown = sa.Column(sa.Boolean)
    sort = sa.Column(sa.Text)
    pattern = sa.Column(sa.Text)
    artist_id = sa.Column(sa.Integer, sa.ForeignKey('artist.id'))

    song_id = relation("Song", backref="song_album", cascade="all, delete")


    def __init__(self, path, name, artist_id, unknown, sort, pattern):
        self.path = path
        self.name = name
        self.artist_id = artist_id
        self.art = False
        self.unknown = unknown
        self.sort = sort
        self.pattern = pattern

    def __repr__(self):
       return "<Album %s `%s`>" % (self.id, self.name)

class History(Base):
    __tablename__ = 'history'

    id = sa.Column(sa.Integer, primary_key=True)
    song_id = sa.Column(sa.Integer, sa.ForeignKey('song.id'))
    selection_time = sa.Column(sa.DateTime)
    user_selected = sa.Column(sa.Boolean)
    skipped = sa.Column(sa.Boolean)

    song_rel = relation("Song", backref="song_history", cascade="all, delete")

    def __init__(self, song_id, user_selected):
        self.song_id = song_id
        self.user_selected = user_selected
        self.selection_time = datetime.datetime.now()
        self.skipped = False

    def __repr__(self):
       return "<History %s %s>" % (self.song_id, self.selection_time)

class Tag(Base):
    __tablename__ = 'tag'

    id = sa.Column(sa.Integer, primary_key=True)
    song_id = sa.Column(sa.Integer, sa.ForeignKey('song.id'))
    tag = sa.Column(sa.Text)
    value = sa.Column(sa.Text)

    song_rel = relation("Song", backref="song_tag", cascade="all, delete")

    def __init__(self, song_id, tag, value):
        self.song_id = song_id
        self.tag = tag
        self.value = value

    def __repr__(self):
       return "<Tag %s %s>" % (self.tag, self.value)

class Scan(Base):
    __tablename__ = 'scan'

    id = sa.Column(sa.Integer, primary_key=True)
    song_id = sa.Column(sa.Integer, sa.ForeignKey('song.id'))
    scan = sa.Column(sa.Text)
    success = sa.Column(sa.Boolean)
    time = sa.Column(sa.DateTime)

    song_rel = relation("Song", backref="song_scan", cascade="all, delete")

    def __init__(self, song_id, scan, success):
        self.song_id = song_id
        self.scan = scan
        self.success = success
        self.time = datetime.datetime.now()

    def __repr__(self):
       return "<Scan %s %s>" % (self.scan, self.success)

engine = sa.create_engine('sqlite:///database.sqlite')
Base.metadata.create_all(engine)

Session = sessionmaker(bind = engine, autocommit = True)
