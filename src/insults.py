
from fraktur.fraktur import encode
import random

insult_file = '../rsc/beleidigungen.txt'
insult_frames_file = '../rsc/beleidigungs_frames.txt'

insults = open(insult_file, encoding="utf_8", mode="r").readlines()
insult_frames = open(insult_frames_file, encoding="utf_8", mode="r").readlines()


def get_insult():
    insult: str = random.choice(insults)
    random_frame: str = random.choice(insult_frames)
    framed_insult: str = random_frame.replace('{{}}', insult)
    return encode(framed_insult)
