#!/usr/bin/env python3
"""
Tests for rss module
"""
from copy import deepcopy
from gettext import gettext
from shutil import rmtree, copytree
from tempfile import mkdtemp
from xml.etree import ElementTree as etree
import os
import unittest

from kiroku import rss as rss_mod
from kiroku import kiroku


class TestRss(unittest.TestCase):
    """Check Rss class"""

    def setUp(self):
        """Setup"""
        self._config = deepcopy(kiroku.CONFIG)
        kiroku.CONFIG.update(kiroku.get_i18n_strings(gettext))
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        copytree(os.path.join(kiroku.DATA_DIR, "templates"), ".templates")

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)
        kiroku.CONFIG = deepcopy(self._config)

    def test_initialization(self):
        """Test initialization"""
        rss = rss_mod.Rss(kiroku.CONFIG)
        self.assertEqual(rss.items, [])

    def test_add(self):
        """Test add method"""
        rss = rss_mod.Rss(kiroku.CONFIG)
        # pass wrong type - expected dict
        self.assertRaises(ValueError, rss.add, "foo")
        # pass wrong argument - expected dict containing title, link, desc and
        # date keys.
        self.assertRaises(KeyError, rss.add, {"foo": "bar"})

        data = {"article_title": "title",
                "article_link": "foo.html",
                "item_desc": "body",
                "pub_date": "2000"}
        rss.add(data)

        self.assertEqual(len(rss.items), 1)

        xml = etree.fromstring(rss.items[0])
        self.assertEqual(len(xml), 5)
        self.assertEqual(xml.tag, 'item')
        self.assertEqual(xml[0].tag, 'title')
        self.assertEqual(xml[0].text, 'title')
        self.assertEqual(xml[1].tag, 'link')
        self.assertEqual(xml[1].text, 'http://localhost/foo.html')
        self.assertEqual(xml[2].tag, 'description')
        self.assertEqual(xml[2].text, 'body')
        self.assertEqual(xml[3].tag, 'pubDate')
        self.assertEqual(xml[3].text, '2000')
        self.assertEqual(xml[4].tag, 'guid')
        self.assertEqual(xml[4].text, 'http://localhost/foo.html')

        data = {"article_title": "title2",
                "article_link": "foo2.html",
                "item_desc": "<p>body2 - \"foo\"</p>",
                "pub_date": "2001"}
        rss.add(data)
        self.assertEqual(len(rss.items), 2)

        xml = etree.fromstring(rss.items[1])
        self.assertEqual(len(xml), 5)
        self.assertEqual(xml.tag, 'item')
        self.assertEqual(xml[0].tag, 'title')
        self.assertEqual(xml[0].text, 'title2')
        self.assertEqual(xml[1].tag, 'link')
        self.assertEqual(xml[1].text, 'http://localhost/foo2.html')
        self.assertEqual(xml[2].tag, 'description')
        self.assertEqual(xml[2].text, '<p>body2 - "foo"</p>')
        self.assertEqual(xml[3].tag, 'pubDate')
        self.assertEqual(xml[3].text, '2001')
        self.assertEqual(xml[4].tag, 'guid')
        self.assertEqual(xml[4].text, 'http://localhost/foo2.html')

    def test_get(self):
        """Test get method"""
        rss = rss_mod.Rss(kiroku.CONFIG)

        xml = etree.fromstring(rss.get())
        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 4)
        self.assertEqual(xml[0].tag, 'channel')
        self.assertEqual(xml[0][0].tag, 'title')
        self.assertEqual(xml[0][0].text, 'Kiroku')
        self.assertEqual(xml[0][1].tag, 'link')
        self.assertEqual(xml[0][1].text, 'http://localhost/')
        self.assertEqual(xml[0][2].tag, 'description')
        self.assertEqual(xml[0][2].text, 'Yet another blog')
        self.assertEqual(xml[0][3].tag, '{http://www.w3.org/2005/Atom}link')

        data = {"article_title": "title",
                "article_link": "foo.html",
                "item_desc": "body",
                "pub_date": "2000"}
        data.update(kiroku.CONFIG)

        rss.add(data)

        xml = etree.fromstring(rss.get())
        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 5)
        self.assertEqual(xml[0].tag, 'channel')
        self.assertEqual(xml[0][0].tag, 'title')
        self.assertEqual(xml[0][0].text, 'Kiroku')
        self.assertEqual(xml[0][1].tag, 'link')
        self.assertEqual(xml[0][1].text, 'http://localhost/')
        self.assertEqual(xml[0][2].tag, 'description')
        self.assertEqual(xml[0][2].text, 'Yet another blog')
        self.assertEqual(xml[0][3].tag, '{http://www.w3.org/2005/Atom}link')
        self.assertEqual(xml[0][4].tag, 'item')
        self.assertEqual(len(xml[0][4]), 5)
        self.assertEqual(xml[0][4][0].tag, 'title')
        self.assertEqual(xml[0][4][0].text, 'title')
        self.assertEqual(xml[0][4][1].tag, 'link')
        self.assertEqual(xml[0][4][4].text, 'http://localhost/foo.html')
        self.assertEqual(xml[0][4][2].tag, 'description')
        self.assertEqual(xml[0][4][2].text, 'body')
        self.assertEqual(xml[0][4][3].tag, 'pubDate')
        self.assertEqual(xml[0][4][3].text, '2000')
        self.assertEqual(xml[0][4][4].tag, 'guid')
        self.assertEqual(xml[0][4][4].text, 'http://localhost/foo.html')


if __name__ == '__main__':
    unittest.main()
