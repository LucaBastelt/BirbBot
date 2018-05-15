import tinify
import os
from configobj import ConfigObj

conf_file = './birb_prefs'


def tinify_folder(folder):

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if os.path.isdir(path):
            print("tinifying folder: {}".format(path))
            tinify_folder(path)
        elif os.path.isfile(path):
            print("tinifying file: {}".format(path))
            source = tinify.from_file(path)
            source.to_file(path)


config = ConfigObj(conf_file)
images_folder = config['images_folder']
tinify_key = config["tinify_key"]

if tinify_key is None or tinify_key is '' or tinify_key == '-':
    print("No tinify key given")
else:
    tinify.key = tinify_key
    tinify_folder(images_folder)
