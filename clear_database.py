import os
import shutil


def clear_database():
    try:
        # delete existing database
        os.remove('database.sqlite')
    except:
        pass

    try:
        # remove art dir
        shutil.rmtree('art')
    except:
        pass

    try:
        os.makedirs('art')
        # copy blank cd cover
        shutil.copyfile('0.jpg', 'art/0.jpg')
    except:
        pass

if __name__ == '__main__':
    clear_database()
