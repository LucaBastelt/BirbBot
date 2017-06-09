#! python3
# The birbs telegram bot
# Github: https://github.com/Zoidster/BirbBot

import telegram.ext
from telegram.ext import Updater
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
import logging
import birbScraper
import glob
import random
import ntpath
import os
import shelve
from configobj import ConfigObj

birbs_folder = './Birbs/'
cache_file = './birb_cache'
conf_file = './birb_prefs'


def get_photos():
    return glob.glob(birbs_folder + '*.jpg')


def get_photo(user: telegram.User):
    settings = shelve.open(cache_file)
    used_pictures = settings.get('used_pictures', {})
    used = used_pictures.get(user.name, [])
    photos = get_photos()
    not_sent = [x for x in photos if x not in used]
    random.shuffle(not_sent)

    if len(photos) == 0:
        return None
    elif len(not_sent) > 0:
        used.append(not_sent[0])
        used_pictures[user.name] = used
        ret = not_sent[0]
    else:
        used_pictures[user.name] = []
        ret = photos[0]

    settings['used_pictures'] = used_pictures
    settings.close()

    return ret


def birb(bot, update):
    print('Sending birb to ' + update.message.from_user.name)
    photo = get_photo(update.message.from_user)
    if photo is None:
        bot.send_message(chat_id=update.message.chat_id, text='There are no more birbs in storage! Whaaaat? Contact '
                                                              '@LucaMN for more birbs!')
    else:
        bot.send_photo(chat_id=update.message.chat_id, photo=open(photo, 'rb'),
                       caption=os.path.splitext(ntpath.basename(photo))[0])


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="I am the birbs bot, I deliver the birbs.\n"
                          "Type /birb receive a brand new birb from our newest collection of premium birbs!")


def show_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Type /birb receive a brand new birb from our newest collection of premium birbs!")


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command. "
                                                          "Type /help to see all commands")


def start_bot(bot_token):
    updater = Updater(token=bot_token)

    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    birb_handler = CommandHandler('birb', birb)
    dispatcher.add_handler(birb_handler)

    help_handler = CommandHandler('help', show_help)
    dispatcher.add_handler(help_handler)

    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()


# Using ConfigObj
# Documentation: http://www.voidspace.org.uk/python/configobj.html
def main():
    print('Reading config from file: {}'.format(conf_file))
    config = ConfigObj(conf_file)

    global birbs_folder
    birbs_folder = config['birbs_folder']
    global cache_file
    cache_file = config['birbs_cache_file']

    print('Scraping birbs')
    reddit_conf = config['reddit']
    birbScraper.start(reddit_conf['reddit_client_id'], reddit_conf['reddit_client_secret'], reddit_conf['reddit_user_agent']
                      , birbs_folder)
    print('Birbs scraped')

    print('Starting telegram bot')
    telegram_conf = config['telegram']
    start_bot(telegram_conf['telegram_bot_token'])
    print('Telegram bot started')

main()
