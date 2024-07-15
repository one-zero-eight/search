import re
import string

from nltk.corpus import stopwords

PUNCT_TO_REMOVE = string.punctuation

_remove_punctuation = str.maketrans("", "", PUNCT_TO_REMOVE)


def remove_punctuation(text):
    """custom function to remove the punctuation"""
    return text.translate(_remove_punctuation)


_remove_stopwords = set(stopwords.words("english") + stopwords.words("russian"))


def remove_stopwords(text):
    """custom function to remove the stopwords"""
    return " ".join([w for w in text.split() if w not in _remove_stopwords])


_remove_html = re.compile(r"<[^>]*>")


def remove_html(text):
    """custom function to remove the html tags"""
    return re.sub(_remove_html, "", text)


def clean_text(text):
    text = remove_html(text)
    text = remove_punctuation(text)
    text = remove_stopwords(text)
    return text
