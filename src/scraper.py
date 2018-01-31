#! python3

import os
import praw
from prawcore import NotFound
import re
import requests
import schedule
import shelve
import hashlib
import time
from threading import Thread


class ScraperConfig:

    def __init__(self, reddit_client_id, reddit_client_secret, reddit_user_agent, shelve_conf_path,
                 shelve_filename_keyword):
        self.client_id = reddit_client_id
        self.client_secret = reddit_client_secret
        self.user_agent = reddit_user_agent
        self.shelve_conf_path = shelve_conf_path
        self.shelve_keyword = shelve_filename_keyword


class Scraper:

    def __init__(self, scraper_config: ScraperConfig, _folder='./Birbs/', _subreddit='birbs'):

        self.folder = _folder
        self.subreddit = _subreddit
        self.scraper_config = scraper_config

    def crawl(self):
        reddit = praw.Reddit(client_id=self.scraper_config.client_id,
                             client_secret=self.scraper_config.client_secret,
                             user_agent=self.scraper_config.user_agent)

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

    def download(self, _url_list, _folder):
        counter = 0

        cache = shelve.open(self.scraper_config.shelve_conf_path)
        file_names = {}
        if self.scraper_config.shelve_keyword in cache:
            file_names = cache[self.scraper_config.shelve_keyword]

        for url in _url_list:
            print('.', end='', flush=True)
            if url.url[-3:] == 'jpg':
                file_name = url.title
                hashed_name = hashlib.md5(file_name.encode()).hexdigest() + '.jpg'
                path = _folder + hashed_name
                if not os.path.isfile(path) and file_name not in file_names.values():
                    img = requests.get(url.url).content
                    with open(path, 'wb') as handler:
                        handler.write(img)
                        file_names[hashed_name] = file_name
                        cache[self.scraper_config.shelve_keyword] = file_names
                    counter += 1
        cache.close()
        return counter

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
