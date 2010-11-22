import sys
from optparse import OptionParser

__version__ = '0.3.6 alpha'

if __name__ == "__main__":
    usage = "usage: %prog [options] package"
    parser = OptionParser(usage=usage)

    parser.add_option("-c", "--clear",
                      action="store_true", dest="clear",
                      help="clear the database and any artwork")

    parser.add_option("-g", "--graphical",
                      action="store_true", dest="graphical",
                      help="start the jukebox in graphical mode")

    parser.add_option("-t", "--text",
                      action="store_true", dest="text",
                      help="start the jukebox in text mode")

    parser.add_option("-f", "--find",
                      action="store", dest="directory", default = None,
                      help="find music in the directory and it's children")

    parser.add_option("-v", "--version",
                      action="store_true", dest="version",
                      help="show version")
    (options, args) = parser.parse_args()

    if options.version:
        print __version__
        sys.exit()

    if options.clear:
        import clear_database
        clear_database.clear_database()

    if options.directory:
        import find_music
        find_music.find_songs(options.directory)

    if options.text:
        import text
        text.start()

    elif options.graphical:
        import graphical
        graphical.start()
