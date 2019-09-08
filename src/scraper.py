#! python3

import random
import praw
import re

imgur_url_pattern = re.compile(r'(http://i.imgur.com/(.*))(\?.*)?')


class ScraperConfig:

    def __init__(self, reddit_client_id, reddit_client_secret, reddit_user_agent):
        self.client_id = reddit_client_id
        self.client_secret = reddit_client_secret
        self.user_agent = reddit_user_agent


class Scraper:

    def __init__(self, scraper_config: ScraperConfig):

        self.scraper_config = scraper_config
        self.reddit = praw.Reddit(client_id=self.scraper_config.client_id,
                                  client_secret=self.scraper_config.client_secret,
                                  user_agent=self.scraper_config.user_agent)

    def get_random_url_from_sub(self, subreddit):

        if not self.sub_exists(subreddit):
            print("Subreddit not found! " + subreddit)
            return

        sub = self.reddit.subreddit(subreddit)
        images = []
        for image in sub.hot(limit=50):
            images.append(image)
        for image in sub.top(limit=50):
            images.append(image)
        random.shuffle(images)
        ret = None
        for post in images:
            ret = self.get_url_and_title(post, False)
            if ret is not None:
                break
        if ret is None:
            for post in images:
                ret = self.get_url_and_title(post, True)
                if ret is not None:
                    break
        return ret

    def sub_exists(self, subreddit):
        exists = True
        try:
            self.reddit.subreddits.search_by_name(subreddit, exact=True)
        except Exception as e:
            exists = False
        return exists

    @staticmethod
    def get_url_and_title(post, url_is_okay):
        ext = post.url[-3:]

        if ext == 'jpg' or ext == 'png':
            return post.url, post.title, False, post.permalink
        else:
            return None if not url_is_okay else (post.url, post.title, True, post.permalink)
