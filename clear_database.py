import os
import shutil


def clear_database():
    try:
        # delete existing database
        os.remove('jukebox.sqlite')
        # remove art dir
        shutil.rmtree('art')
        os.makedirs('art')
        # copy blank cd cover
        shutil.copyfile('0.jpg', 'art/0.jpg')
    except:
        pass

if __name__ == 'main':
    clear_database()
