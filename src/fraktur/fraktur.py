"""
    Source: https://github.com/carpedm20/fraktur
    Distributed under MIT License
"""

from .code import encodeCode

umlaute = {
    'ä': 'ae',
    'ü': 'ue',
    'ö': 'oe',
    'Ä': 'Ae',
    'Ü': 'Ue',
    'Ö': 'Oe',
    'ß': 'ss',
    '\n': '',
    '\r': '',
}


def encode(text: str):
    for key, val in umlaute.items():
        text = text.replace(key, val)
    return text.translate(encodeCode)
