#! python3

import os
import praw
from prawcore import NotFound
import re
import requests
import schedule
import time
from threading import Thread


class RedditConfig:

    def __init__(self, reddit_client_id, reddit_client_secret, reddit_user_agent):
        self.client_id = reddit_client_id
        self.client_secret = reddit_client_secret
        self.user_agent = reddit_user_agent


class Scraper:

    def __init__(self, reddit_config: RedditConfig, _folder='./Birbs/', _subreddit='birbs'):

        self.folder = _folder
        # print('Set folder as {}'.format(_folder))
        self.subreddit = _subreddit
        # print('Set subreddit as {}'.format(_subreddit))
        self.client_id = reddit_config.client_id
        # print('Set reddit client id as {}'.format(client_id))
        self.client_secret = reddit_config.client_secret
        # print('Set reddit client secret as {}'.format(client_secret))
        self.user_agent = reddit_config.user_agent
        # print('Set reddit user agent as {}'.format(user_agent))

    def crawl(self):
        reddit = praw.Reddit(client_id=self.client_id,
                             client_secret=self.client_secret,
                             user_agent=self.user_agent)

        if not self.sub_exists(self.subreddit, reddit):
            print("Subreddit not found! " + self.subreddit)
            return

        print('Running downloader on folder: {}'.format(self.folder))

        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        images = reddit.subreddit(self.subreddit)

        counter = 0

        counter += self.download(images.hot(limit=30), self.folder)
        counter += self.download(images.top(limit=30), self.folder)
        print('')
        print('Download complete, loaded {} new images'.format(counter))

    def start(self):

        print('Starting new scraper for subreddit {} for folder {}'.format(self.subreddit, self.folder))

        self.crawl()
        schedule.every().day.do(self.crawl)
        thread = Thread(target=self.update)
        thread.start()
        print('Started update Thread')

    @staticmethod
    def update():
        while True:
            schedule.run_pending()
            time.sleep(30)

    @staticmethod
    def sub_exists(sub, reddit):
        exists = True
        try:
            reddit.subreddits.search_by_name(sub, exact=True)
        except NotFound:
            exists = False
        return exists

    @staticmethod
    def download(_url_list, _folder):
        counter = 0
        for url in _url_list:
            print('.', end='', flush=True)
            if url.url[-3:] == 'jpg':
                file_name = re.sub(r"[^\w\s]+", '', url.title)
                file_name = _folder + file_name + '.jpg'
                if not os.path.isfile(file_name):
                    img = requests.get(url.url).content
                    with open(file_name, 'wb') as handler:
                        handler.write(img)
                    counter += 1
        return counter
