#! python3
# The birbs telegram bot
# Github: https://github.com/Zoidster/BirbBot

import telegram.ext
from telegram.ext import Updater
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
import logging
import glob
import random
import ntpath
import os
import re
import shelve
from configobj import ConfigObj

from scraper import Scraper, ScraperConfig

cache_used_images_keyword = 'used_pictures'
shelve_filename_keyword = 'filename_hashes'


# Using ConfigObj
# Documentation: http://www.voidspace.org.uk/python/configobj.html
class BirbBot:
    def __init__(self, config_file):

        self.conf_file = config_file

        print('Reading config from file: {}'.format(self.conf_file))
        config = ConfigObj(self.conf_file)

        self.birbs_folder = config['birbs_folder']
        self.others_folder = config['other_images_folder']
        self.cache_file = config['birbs_cache_file']
        self.birbs_subreddit = config['birbs_subreddit']

        reddit_conf = config['reddit']

        self.reddit_config = ScraperConfig(reddit_conf['reddit_client_id'],
                                           reddit_conf['reddit_client_secret'],
                                           reddit_conf['reddit_user_agent'],
                                           self.cache_file, shelve_filename_keyword)

        start_new_scraper(self.birbs_subreddit, self.birbs_folder, self.reddit_config)

        if 'subreddits' in config:
            for subreddit in config['subreddits']:
                print('Adding scraper for subreddit {} to folder {}'.format(subreddit, config['subreddits'][subreddit]))
                start_new_scraper(subreddit, '{}/{}/'.format(self.others_folder, config['subreddits'][subreddit]),
                                  self.reddit_config)

        print('Starting telegram bot')
        telegram_conf = config['telegram']
        self.start_bot(telegram_conf['telegram_bot_token'])
        print('Telegram bot started')

    def start_bot(self, bot_token):
        updater = Updater(token=bot_token)

        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        start_handler = CommandHandler('start', self.start_callback)
        dispatcher.add_handler(start_handler)

        birb_handler = CommandHandler('birb', self.birb_callback)
        dispatcher.add_handler(birb_handler)

        help_handler = CommandHandler('help', self.show_help_callback)
        dispatcher.add_handler(help_handler)

        add_handler = CommandHandler('add', self.add_callback, pass_args=True)
        dispatcher.add_handler(add_handler)

        unknown_handler = MessageHandler(Filters.command, self.unknown_callback)
        dispatcher.add_handler(unknown_handler)

        updater.start_polling()

    def birb_callback(self, bot, update):
        print('Sending birb to ' + update.message.from_user.name + ' - ' + update.message.text)
        photo, title = get_photo(update.message.from_user, self.cache_file, self.birbs_folder)
        if photo is None:
            bot.send_message(chat_id=update.message.chat_id,
                             text='There are no more birbs in storage! Whaaaat? Contact '
                                  '@LucaMN for more birbs!')
        else:
            bot.send_photo(chat_id=update.message.chat_id, photo=open(photo, 'rb'),
                           caption=title)

    def start_callback(self, bot, update):
        other_image_folders = set([name for name in os.listdir(self.others_folder)
                                   if os.path.isdir(os.path.join(self.others_folder, name))])
        bot.send_message(chat_id=update.message.chat_id,
                         text='I am the birbs bot, I deliver the birbs.\n'
                              'Type /birb receive a brand new birb from our newest collection of premium birbs!.\n'
                              'Other content is available via the the following commands:\n' +
                              ', '.join(other_image_folders) + '\n' +
                              'Code located at https://github.com/Zoidster/BirbBot\n'
                              'Author: @LucaMN')

    def show_help_callback(self, bot, update):
        other_image_folders = set([name for name in os.listdir(self.others_folder)
                                   if os.path.isdir(os.path.join(self.others_folder, name))])
        bot.send_message(chat_id=update.message.chat_id,
                         text='Type /birb receive a brand new birb from our newest collection of premium birbs!\n' +
                              'Other content is available via the the following commands:\n' +
                              ', '.join(other_image_folders) + '\n' +
                              'Code located at https://github.com/Zoidster/BirbBot\n'
                              'Author: @LucaMN')

    def add_callback(self, bot, update, args):
        config = ConfigObj(self.conf_file)

        # The subreddit is the name of the subreddit to pull the images from. It has to be alphanumeric
        subreddit = re.sub(r'\W+', '', args[0])

        # The handle is the folder and command the images will be accessible over. Also alphanumeric
        if len(args) > 1:
            handle = re.sub(r'\W+', '', args[1])
        else:
            handle = subreddit

        if 'subreddits' not in config:
            config['subreddits'] = {subreddit: handle}
            config.write()
        else:
            config['subreddits'][subreddit] = handle
            config.write()

        bot.send_message(chat_id=update.message.chat_id,
                         text="Added the new subreddit to scrape, please wait a bit until the download is complete!")

        start_new_scraper(subreddit, '{}/{}/'.format(self.others_folder, config['subreddits'][subreddit]),
                          self.reddit_config)

        bot.send_message(chat_id=update.message.chat_id,
                         text="Scraping complete, {} images now available".format(handle))

    def unknown_callback(self, bot, update):
        if self.others_folder != '':
            other_image_folders = [name for name in os.listdir(self.others_folder)
                                   if os.path.isdir(os.path.join(self.others_folder, name))]
            command = update.message.text[1:].split('@')[0]
            print('Special image requested, command: '.format(command) + ' - ' + update.message.text)

            if command in other_image_folders:
                print('Sending {} to {}'.format(command, update.message.from_user.name))
                photo, title = get_photo(update.message.from_user, self.cache_file, self.others_folder + '/' + command + '/')
                if photo is None:
                    bot.send_message(chat_id=update.message.chat_id,
                                     text='There are no images in storage for that keyword.')
                else:
                    bot.send_photo(chat_id=update.message.chat_id, photo=open(photo, 'rb'),
                                   caption=title)
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.\n"
                                                                      "Type /help to see all commands")


def get_photo(user, cache_file, folder):
    settings = shelve.open(cache_file)
    used_pictures = settings.get(cache_used_images_keyword, {})
    used = used_pictures.get(user.name, [])

    photos = get_photos(folder)

    not_sent = [x for x in photos if x not in used]
    random.shuffle(not_sent)

    if len(photos) == 0:
        return None
    elif len(not_sent) > 0:
        used.append(not_sent[0])
        used_pictures[user.name] = used
        photo = not_sent[0]
    else:
        used_pictures[user.name] = [photos[0]]
        photo = photos[0]

    settings[cache_used_images_keyword] = used_pictures

    file_names = settings[shelve_filename_keyword]
    if ntpath.basename(photo) in file_names:
        title = file_names[ntpath.basename(photo)]
    else:
        title = os.path.splitext(ntpath.basename(photo))[0]

    settings.close()
    return photo, title


def get_photos(command):
    return glob.glob(command + '*.jpg')


def start_new_scraper(subreddit, folder, reddit_config):
    s = Scraper(reddit_config,
                folder, subreddit)
    s.start()
