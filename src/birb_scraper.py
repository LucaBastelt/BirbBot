#! python3

import os
import praw
import re
import requests
import schedule
import time
from threading import Thread

folder = ''
subreddit = 'birbs'
client_id = ''
client_secret = ''
user_agent = ''

counter = 0


def crawl():
    print('Running downloader on folder: {}'.format(folder))
    if not os.path.exists(folder):
        os.makedirs(folder)

    reddit = praw.Reddit(client_id=client_id,
                         client_secret=client_secret,
                         user_agent=user_agent)

    birbs = reddit.subreddit(subreddit)

    global counter
    counter = 0

    download(birbs.hot())
    download(birbs.top())
    print('')
    print('Download complete, loaded {} new birbs'.format(counter))


def download(birb_list):
    global counter
    for birb in birb_list:
        print('.', end='', flush=True)
        if birb.url[-3:] == 'jpg':
            file_name = re.sub(r"[^\w\s]+", '', birb.title)
            file_name = folder + file_name + '.jpg'
            if not os.path.isfile(file_name):
                img = requests.get(birb.url).content
                with open(file_name, 'wb') as handler:
                    handler.write(img)
                counter += 1


def start(_client_id, _client_secret, _user_agent, _folder='./Birbs/'):
    global folder
    folder = _folder
    # print('Set birbs folder as {}'.format(_folder))
    global client_id
    client_id = _client_id
    # print('Set reddit client id as {}'.format(client_id))
    global client_secret
    client_secret = _client_secret
    # print('Set reddit client secret as {}'.format(client_secret))
    global user_agent
    user_agent = _user_agent
    # print('Set reddit user agent as {}'.format(user_agent))

    crawl()
    schedule.every().day.do(crawl)
    thread = Thread(target=update)
    thread.start()
    print('Started update Thread')


def update():
    while True:
        schedule.run_pending()
        time.sleep(30)
