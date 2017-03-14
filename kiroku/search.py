"""
Indexer and search word provider

Note, that no stemming, nor other lexical analysis are done here. It's
somehow hard to do it right statically for Polish language. For sure there
are existing ready solutions for such task implemented for English language
(see Sphinx project or https://pypi.python.org/pypi/stemming)
"""
import collections
from html import parser
import re


class MLStripper(parser.HTMLParser):
    """Find and store words from the HTML string."""

    def __init__(self, **kwargs):
        """Initialize. tag_stack will help to keep track on which tag we are,
        words is a container for the data"""
        super().__init__(**kwargs)
        self.reset()
        self.tag_stack = ['root']
        self.words = collections.defaultdict(list)

    def handle_starttag(self, tag, attrs):
        """Store the tag on the stack"""
        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        """Remove last tag from the stack"""
        self.tag_stack.pop()

    def handle_data(self, data):
        """Get the string in the tag, attach weight to every word on the
        string and append it to the dict of list."""
        weight_map = {'h1': 4,
                      'h2': 4,
                      'h3': 4,
                      'h4': 3,
                      'h5': 3,
                      'h6': 3,
                      'a': 3,
                      'b': 2,
                      'i': 2}
        weight = weight_map.get(self.tag_stack[-1], 1)
        data = re.sub(r"[^\w0-9]+", " ", data)
        for word in data.split():
            self.words[word.lower()].append(weight)

    def get_data(self):
        """Return dictionary containning words as the keys and weights as a
        values"""
        weights = collections.defaultdict(list)
        for key in self.words:
            if len(key) > 1:  # skip one letter items
                weight = sum(self.words[key])
                weights[key] = weight
        return dict(weights)
