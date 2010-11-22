import os
import shutil


def clear_database():
    app_path = os.path.dirname(os.path.abspath(__file__))
    try:
        # delete existing database
        os.remove(os.path.join(app_path, 'database.sqlite'))
    except:
        pass

    try:
        # remove art dir
        shutil.rmtree(os.path.join(app_path, 'art'))
    except:
        pass

    try:
        os.makedirs(os.path.join(app_path, 'art'))
        # copy blank cd cover
        shutil.copyfile(os.path.join(app_path, '0.jpg'), os.path.join(app_path, 'art/0.jpg'))
    except:
        pass

if __name__ == '__main__':
    clear_database()
