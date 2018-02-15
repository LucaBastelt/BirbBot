from birbs_bot import BirbBot
import os.path
conf_file = './birb_prefs'

if not os.path.isfile(conf_file):
    print("Please enter a valid config file path!")
else:
    bot = BirbBot(conf_file)
