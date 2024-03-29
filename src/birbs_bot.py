#! python3
# The birbs telegram bot
# Github: https://github.com/Zoidster/BirbBot

import logging

import telegram.ext
from configobj import ConfigObj
from telegram import Update
from telegram.error import (Unauthorized)
from telegram.ext import CommandHandler, CallbackContext
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from scraper import Scraper, ScraperConfig
from insults import get_insult

cache_subscriptions = 'subs'
cache_subreddits = 'subreddits'


# Using ConfigObj
# Documentation: http://www.voidspace.org.uk/python/configobj.html
class BirbBot:
    def __init__(self, config_file):

        self.conf_file = config_file

        print('Reading config from file: {}'.format(self.conf_file))
        config = ConfigObj(self.conf_file)

        self.birbs_subreddit = config['birbs_subreddit']

        reddit_conf = config['reddit']

        self.reddit_config = ScraperConfig(reddit_conf['reddit_client_id'],
                                           reddit_conf['reddit_client_secret'],
                                           reddit_conf['reddit_user_agent'])

        self.scraper = Scraper(self.reddit_config)

        print('Starting telegram bot')
        telegram_conf = config['telegram']
        self.start_bot(telegram_conf['telegram_bot_token'])
        print('Telegram bot started')

    def start_bot(self, bot_token):
        updater = Updater(token=bot_token, use_context=True)

        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        dispatcher.add_handler(CommandHandler('start', self.start_callback))
        dispatcher.add_handler(CommandHandler('birb', self.birb_callback))
        dispatcher.add_handler(CommandHandler('subscribe', self.subscribe, pass_args=True))
        dispatcher.add_handler(CommandHandler('unsubscribe', self.unsubscribe, pass_args=True))
        dispatcher.add_handler(CommandHandler('help', self.show_help))
        dispatcher.add_handler(CommandHandler('1839', self.insult))
        dispatcher.add_handler(CommandHandler('beleidigung', self.insult))
        dispatcher.add_handler(MessageHandler(Filters.command, self.unknown_callback))

        updater.start_polling()

        j = updater.job_queue
        j.run_repeating(self.send_subs, interval=3600, first=600)

    def send_subs(self, context: CallbackContext):
        config = ConfigObj(self.conf_file)
        to_remove = []
        if cache_subscriptions not in config:
            return
        for chat in config[cache_subscriptions]:
            for subreddit in config[cache_subscriptions][chat]:
                try:
                    print('Sending {} to chat {}'.format(subreddit, chat))
                    self.send_photo(context.bot, chat, subreddit)
                except Unauthorized as e:
                    to_remove.append(chat)
                    print("removing chat from subs: {}\nError: {}".format(chat, e))
                except Exception as e:
                    to_remove.append(chat)
                    print("removing chat from subs: {}\nError: {}".format(chat, e))

        # config[cache_subscriptions] = [x for x in config[cache_subscriptions] if x not in to_remove]
        # config.write()

    def birb_callback(self, update: Update, context: CallbackContext):
        print('Sending birb to ' + update.message.from_user.name + ' - ' + update.message.text)
        self.send_photo(context.bot, update.message.chat_id, 'birb')

    def start_callback(self, update: Update, context: CallbackContext):
        config = ConfigObj(self.conf_file)
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=f'I am the birbs bot, I deliver the birbs.\n' \
                                      f'Type /birb receive a brand new birb from our newest collection of premium birbs!.\n' \
                                      f'Other content is available via the the following commands:\n' \
                                      f'{", ".join(config[cache_subreddits])}\n' \
                                      f'Code located at https://github.com/Zoidster/BirbBot\nAuthor: @LucaMN')

    def subscribe(self, update: Update, context: CallbackContext):
        if len(context.args) == 0:
            context.args = [self.birbs_subreddit]
        chat = str(update.message.chat_id)
        config = ConfigObj(self.conf_file)
        if cache_subscriptions not in config:
            config[cache_subscriptions] = {}
            config.write()
            config.reload()
        if chat not in config[cache_subscriptions]:
            config[cache_subscriptions][chat] = []
            config.write()
            config.reload()

        for subreddit in context.args:
            if subreddit not in config[cache_subscriptions][chat]:
                chat_subs = config[cache_subscriptions][chat]
                chat_subs.append(subreddit)
                config.write()
                config.reload()
                print(f'Subscribtion of {subreddit} for chat {chat}')
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=f'Subscription successful! Sending an image from {subreddit} every hour')
            else:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=f'You are already subscribed to {subreddit}!')

    def unsubscribe(self, update: Update, context: CallbackContext):
        chat = str(update.message.chat_id)
        config = ConfigObj(self.conf_file)
        if cache_subscriptions not in config or chat not in config[cache_subscriptions]:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text='Unsubscription unsuccessful! You are not subscribed to anything')
            return

        for folder in context.args:
            if folder in config[cache_subscriptions][chat]:
                chat_subs = config[cache_subscriptions][chat]
                chat_subs.remove(folder)
                config[cache_subscriptions][chat] = chat_subs
                config.write()
                config.reload()
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=f'Unsubscription successful! Not sending images from {folder} anymore')
            else:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text=f'Unsubscription unsuccessful! You are not subscribed to {folder}')

    def show_help(self, update: Update, context: CallbackContext):
        config = ConfigObj(self.conf_file)
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=f'Type /birb receive a brand new birb from our newest collection of premium birbs!\n' \
                                      f'Other content is available via the the following commands:\n' \
                                      f'{", ".join(config[cache_subreddits])}\n' \
                                      f'Use the subscribe command with any amount of arguments to get hourly images\n' \
                                      f'Code located at https://github.com/Zoidster/BirbBot\nAuthor: @LucaMN')

    def insult(self, update: Update, context: CallbackContext):
        insult = get_insult()
        print('Sending insult to ' + update.message.from_user.name + ' - ' + insult)
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=f'{insult}')

    def unknown_callback(self, update: Update, context: CallbackContext):
        command = update.message.text[1:].split('@')[0]
        print('Sending {} to {}'.format(command, update.message.from_user.name))
        self.send_photo(context.bot, update.message.chat_id, command)

    def send_photo(self, bot, chat, subreddit):
        if subreddit == 'birb':
            subreddit = self.birbs_subreddit

        if self.scraper.sub_exists(subreddit):
            url, title, send_as_url, permalink = self.scraper.get_random_url_from_sub(subreddit)

            if url is None:
                bot.send_message(chat_id=chat,
                                 text='There are no images for the keyword {}'.format(subreddit))
            else:

                try:
                    link = f"[Link](https://reddit.com{permalink})"
                    print(link)
                    if not send_as_url:
                        bot.sendChatAction(chat_id=chat, action=telegram.ChatAction.UPLOAD_PHOTO)
                        bot.send_photo(chat_id=chat, photo=url, caption=title)
                        bot.send_message(chat_id=chat, text=link,
                                         parse_mode=telegram.ParseMode.MARKDOWN,
                                         disable_web_page_preview=True)
                    else:
                        bot.send_message(chat_id=chat, text=url)
                        bot.send_message(chat_id=chat, text=title)
                        bot.send_message(chat_id=chat, text=link,
                                         parse_mode=telegram.ParseMode.MARKDOWN,
                                         disable_web_page_preview=True)
                except:
                    bot.send_message(chat_id=chat,
                                     text=f"Internal error, please try again <3")
        else:
            bot.send_message(chat_id=chat,
                             text=f"Sorry, the command {subreddit} is not valid.\n Type /help to see all commands")
