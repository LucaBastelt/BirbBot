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

shelve_filename_keyword = 'filename_hashes'
cache_subs = 'subs'


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

        subscribe_handler = CommandHandler('subscribe', self.subscribe_callback, pass_args=True)
        dispatcher.add_handler(subscribe_handler)

        unsubscribe_handler = CommandHandler('unsubscribe', self.unsubscribe_callback, pass_args=True)
        dispatcher.add_handler(unsubscribe_handler)

        help_handler = CommandHandler('help', self.show_help_callback)
        dispatcher.add_handler(help_handler)

        add_handler = CommandHandler('add', self.add_callback, pass_args=True)
        dispatcher.add_handler(add_handler)

        unknown_handler = MessageHandler(Filters.command, self.unknown_callback)
        dispatcher.add_handler(unknown_handler)

        updater.start_polling()

        j = updater.job_queue
        j.run_repeating(self.callback_subs, interval=3600, first=0)

    def callback_subs(self, bot, job):
        config = ConfigObj(self.conf_file)
        if cache_subs not in config:
            return
        for chat in config[cache_subs]:
            for folder in config[cache_subs][chat]:
                print('Sending {} to chat {}'.format(folder, chat))
                self.send_photo(bot, chat, folder)

    def birb_callback(self, bot, update):
        print('Sending birb to ' + update.message.from_user.name + ' - ' + update.message.text)
        self.send_birb(bot, update.message.chat_id)

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

    def subscribe_callback(self, bot, update, args):
        if len(args) == 0:
            args = ['birbs']
        chat = str(update.message.chat_id)
        config = ConfigObj(self.conf_file)
        if cache_subs not in config:
            config[cache_subs] = {}
            config.write()
            config.reload()
        if chat not in config[cache_subs]:
            config[cache_subs][chat] = []
            config.write()
            config.reload()

        for folder in args:
            if folder not in config[cache_subs][chat]:
                chat_subs = config[cache_subs][chat]
                chat_subs.append(folder)
                config[cache_subs][chat] = chat_subs
                config.write()
                config.reload()
                bot.send_message(chat_id=update.message.chat_id,
                                 text='Subscription successful! Sending an image from {} every hour'.format(folder))
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 text='You are already subscribed to that!')

    def unsubscribe_callback(self, bot, update, args):
        chat = str(update.message.chat_id)
        config = ConfigObj(self.conf_file)
        if cache_subs not in config:
            return
        if chat not in config[cache_subs]:
            return

        for folder in args:
            if folder in config[cache_subs][chat]:
                chat_subs = config[cache_subs][chat]
                chat_subs.remove(folder)
                config[cache_subs][chat] = chat_subs
                config.write()
                config.reload()
                bot.send_message(chat_id=update.message.chat_id,
                                 text='Unsubscription successful! Not sending images from {} anymore'.format(folder))
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 text='Unsubscription unsuccessful! You are not subscribed to {}'.format(folder))

    def show_help_callback(self, bot, update):
        other_image_folders = set([name for name in os.listdir(self.others_folder)
                                   if os.path.isdir(os.path.join(self.others_folder, name))])
        bot.send_message(chat_id=update.message.chat_id,
                         text='Type /birb receive a brand new birb from our newest collection of premium birbs!\n' +
                              'Other content is available via the the following commands:\n' +
                              ', '.join(other_image_folders) + '\n' +
                              'Use the subscribe command with any amount of arguments to get hourly images\n'
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
            command = update.message.text[1:].split('@')[0]
            print('Sending {} to {}'.format(command, update.message.from_user.name))
            self.send_photo(bot, update.message.chat_id, command)

    def send_birb(self, bot, chat):
        self.send_photo(bot, chat, 'birb')

    def send_photo(self, bot, chat, command):
        if command == 'birbs' or command == 'birb':
            photo, title = get_photo(self.cache_file, self.birbs_folder)
            if photo is None:
                bot.send_message(chat_id=chat,
                                 text='There are no more birbs in storage! Contact '
                                      '@LucaMN for more birbs!')
            else:
                bot.send_photo(chat_id=chat, photo=open(photo, 'rb'),
                               caption=title)
        else:
            other_image_folders = [name for name in os.listdir(self.others_folder)
                                   if os.path.isdir(os.path.join(self.others_folder, name))]

            if command in other_image_folders:
                photo, title = get_photo(self.cache_file, self.others_folder + '/' + command + '/')
                if photo is None:
                    bot.send_message(chat_id=chat,
                                     text='There are no images in storage for the keyword {}'.format(command))
                else:
                    bot.send_photo(chat_id=chat, photo=open(photo, 'rb'),
                                   caption=title)
            else:
                bot.send_message(chat_id=chat,
                                 text="Sorry, I didn't understand the command {}.\nType /help to see all commands".format(
                                     command))


def get_photo(cache_file, folder):
    settings = shelve.open(cache_file)

    photos = get_photos(folder)

    random.shuffle(photos)

    if len(photos) == 0:
        return None
    else:
        photo = photos[0]

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
