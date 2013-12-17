"""
RSS class responsible for managing entries in RSS feed and generating XML for
kiroku
"""
from kiroku.template import Template


class Rss:
    """Rss representation class"""
    def __init__(self, cfg):
        """Initialize RSS container"""
        self.items = []
        self._templ = Template(cfg)
        self._cfg = cfg

    def add(self, item):
        """Add rss item to the list. Parameter item is a dictionary which
        contains 4 keys with corresponding values:

            title - title of the article
            link - link to the article
            desc - description/first paragraph of the article
            date - publish date in format "Sun, 29 Sep 2002 19:09:28 GMT"
        """
        self.items.append(self._templ("rss_item", item))

    def get(self):
        """Return RSS XML string"""
        return self._templ("rss_main", {"items": "\n".join(self.items)})
