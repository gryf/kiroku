"""
Article class for article representation in kiroku
"""
from datetime import datetime
import locale
import os
import re

from kiroku.rest import BlogArticle
from kiroku.naive_tzinfo import get_rfc3339, get_rfc822
from kiroku.search import MLStripper
from kiroku.misc import TR_TABLE


class Article:
    """Represents article"""

    def __init__(self, fname, cfg):
        """Create the obj"""
        self._fname = fname
        self.body = None
        self.created = None
        self.html_fname = None
        self.tags = []
        self.title = None
        self._cfg = cfg

    def read(self):
        """Read article and transform to html"""
        self.body, attrs = self._transfrom_to_html()
        self._process_attrs(attrs)
        self._set_html_name()

    def get_words(self):
        """Return word dictionary out of the html and article attributes"""
        ml_stripper = MLStripper(strict=False)
        ml_stripper.feed(self.body)
        return ml_stripper.get_data()

    def created_short(self):
        """Return human created date"""
        return self.created.strftime("%d %b, %Y")

    def created_detailed(self):
        """Return human created date"""
        return self.created.strftime("%A, %d %b, %Y, %X")

    def created_rfc3339(self):
        """Return RFC 3339 formatted date"""
        return get_rfc3339(self.created, self._cfg['timezone'])

    def created_rfc822(self):
        """Return RFC 822 formatted date"""
        # RFC 822 doesn't allow localized strings
        locale.setlocale(locale.LC_ALL, "C")
        date = get_rfc822(self.created, self._cfg['timezone'])
        locale.setlocale(locale.LC_ALL, self._cfg["locale"])
        return date

    def _transfrom_to_html(self):
        """Return processed article and its fields"""
        html = attrs = None
        with open(self._fname) as fobj:
            html, attrs = BlogArticle(fobj.read()).publish()
        return html, attrs

    def _process_attrs(self, attrs):
        """Process provided article attributes"""
        action_map = {'datetime': self._set_ctime,
                      'tags': self._set_tags,
                      'title': self._set_title}

        for key in attrs:
            if action_map.get(key):
                action_map[key](attrs[key])

        if not self.created:
            self._set_ctime()

        if not self.title:
            self.title = os.path.splitext(os.path.basename(self._fname))[0]

    def _set_ctime(self, date_str=None):
        """Set article creation time either with provided date_str, or via
        article files' mtime."""
        if date_str:
            self.created = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            mtime = os.stat(self._fname).st_mtime
            self.created = datetime.fromtimestamp(mtime)

    def _set_tags(self, tags_str):
        """Process tags into a list. List of tags is sorted in alphabetical
        order"""
        tags = []
        for tag in tags_str.split(","):
            tag = tag.strip()
            tags.append(tag)
        tags.sort()

        self.tags = tags

    def _set_title(self, title):
        """Set title out of provided title."""
        if title:
            self.title = title

    def _set_html_name(self):
        """Caclulate html uri part"""
        # Files are sometimes named:
        # YYYY-MM-DD_some_informative_name.rst
        re_fname = re.compile(r"\d{4}-\d{2}-\d{2}_(.*)")

        dummy, name = os.path.split(self._fname)
        name, dummy = os.path.splitext(name)

        name = name.translate(TR_TABLE)

        match = re_fname.match(name)
        if match:
            # remove the prepending dates out of filename
            self.html_fname = match.groups()[0].replace("_", "-") + ".html"
        else:
            # default.
            name, dummy = os.path.splitext(name)
            name = name.replace("_", "-")
            self.html_fname = name + ".html"

    def get_short_body(self):
        """Return part of the HTML body up to first <!-- more --> comment"""
        return self.body.split("<!-- more -->")[0].strip()
