#!/usr/bin/env python3
# encoding: utf-8
"""
Tests for reStructuredText translator and writer
"""
from datetime import datetime, timedelta
from gettext import gettext
from shutil import rmtree, copytree
from tempfile import mkdtemp
from xml.etree import ElementTree as etree
import json
import os
import shutil
import time
import unittest

from kiroku import kiroku


MOCK_ARTICLES = {'empty.rst': ('', int(time.mktime((2010, 10, 10, 10, 10, 10,
                                                    0, 0, 0)))),
                 'complete.rst': (':Title: Kiroku\n'
                                  ':Datetime: 2013-09-08 10:57:24\n'
                                  ':Modified:\n'
                                  ':Tags: blog\n\n'
                                  'Kiroku\n-------\n\n'
                                  'Arcu scelerisque aliquam. Nullam viverra '
                                  'magna vitae leo. **Vestibulum** in lacus '
                                  'sit amet lectus tempus aliquet.',
                                  int(time.mktime((2012, 12, 12, 12, 12, 12,
                                                   0, 0, 0)))),
                 'incomplete.rst': ('body, body',
                                    int(time.mktime((2011, 11, 11, 11, 11, 11,
                                                     0, 0, 0)))),
                 'minimal.rst': (':Title: title\n:Datetime: 2000-01-01'
                                 ' 11:11:11\n:Tags: foo\n\nbody, body',
                                 int(time.mktime((2001, 1, 1, 1, 1, 1, 0, 0,
                                                  0)))),
                 'about.rst': ('Hi, my name is',
                               int(time.mktime((2002, 2, 2, 2, 2, 2, 0, 0,
                                                0)))),
                 'full.rst': (':Title: Kiroku\n'
                              ':Datetime: 2013-09-08 10:57:24\n'
                              ':Modified:\n'
                              ':Tags: blog\n\n'
                              'Kiroku\n-------\n\n'
                              'Lorem ipsum dolor sit amet, consectetur '
                              'adipiscing elit.\n\n'
                              '.. more\n\n'
                              'Arcu scelerisque aliquam. Nullam viverra magna '
                              'vitae leo. ',
                              int(time.mktime((2005, 5, 5, 5, 5, 5, 0, 0,
                                               0))))}


class MockKiroku:
    """Fake Kiroku class"""
    def __init__(self, cfg):
        """Mock init method"""

    def build(self):
        """Fake build method"""
        return 0

    def init(self, target_path):
        """Fake init method"""
        return 0


class MockArgParse:
    """Fake ArgumentParser class"""
    def __init__(self):
        self.dir_or_path = True


class TestArticle(unittest.TestCase):
    """Check Article class"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
        kiroku.CONFIG.update(kiroku.get_i18n_strings(gettext))
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        os.mkdir('articles')

        for fname, content in MOCK_ARTICLES.items():
            full_path = os.path.join('articles', fname)
            with open(full_path, "w") as fobj:
                fobj.write(content[0])
                os.utime(full_path, (content[1], content[1]))

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)

    def test_initialization(self):
        """Tests initialization of the article"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

        art_fname = os.path.join('articles', "minimal.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

    def test__transfrom_to_html(self):
        """Test _transfrom_to_html method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        html, attrs = art._transfrom_to_html()
        self.assertEqual(attrs, {})
        self.assertEqual(html, '')

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        html, attrs = art._transfrom_to_html()
        self.assertEqual(attrs, {'datetime': '2013-09-08 10:57:24',
                                 'tags': 'blog',
                                 'title': 'Kiroku'})
        self.assertIn('<h2>Kiroku</h2>', html)
        self.assertIn('<p>Arcu', html)
        self.assertIn('aliquet.</p>', html)
        self.assertIn('<strong>Vestibulum</strong>', html)
        self.assertNotIn('<!-- more -->', html)

        art_fname = os.path.join('articles', "full.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        html, attrs = art._transfrom_to_html()
        self.assertEqual(attrs, {'datetime': '2013-09-08 10:57:24',
                                 'tags': 'blog',
                                 'title': 'Kiroku'})
        self.assertIn('<h2>Kiroku</h2>', html)
        self.assertIn('<p>Lorem', html)
        self.assertIn('elit.</p>', html)
        self.assertIn('<!-- more -->', html)
        self.assertIn('<p>Arcu', html)
        self.assertIn('leo.</p>', html)

    def test__set_html_name(self):
        """Test _set_html_name method"""
        art = kiroku.Article(None, kiroku.CONFIG)
        self.assertRaises(AttributeError, art._set_html_name)

        art = kiroku.Article("foobar", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = kiroku.Article("foobar?", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = kiroku.Article("~fo'o'bar. Oto smok!!!.txt", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "fo-o-bar-Oto-smok.html")

        art = kiroku.Article("\\who is using such silly names?."
                             " żółty smok%.article", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname,
                         "who-is-using-such-silly-names-zolty-smok.html")

        art = kiroku.Article("2000-04-01_This is a joke.rst", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "This-is-a-joke.html", kiroku.CONFIG)

    def test__set_ctime(self):
        """Test _set_ctime method"""
        # if no file is passed to the Article constructor, trying to open None
        # object as an argument for open() function will cause exception
        art = kiroku.Article(None, kiroku.CONFIG)
        self.assertRaises(TypeError, art._set_ctime)

        # Try to caclulate creation time with the file mtime
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art._set_ctime()
        self.assertEqual(art.created,
                         datetime.strptime("20101010111010", "%Y%m%d%H%M%S"))

        # Process field 'datetime' as an Article creation time
        art = kiroku.Article(None, kiroku.CONFIG)
        art._set_ctime('1998-07-06 21:12:21')
        self.assertEqual(art.created,
                         datetime.strptime("19980706211221", "%Y%m%d%H%M%S"))

    def test__set_tags(self):
        """Test _set_tags method"""
        art = kiroku.Article(None, kiroku.CONFIG)
        self.assertRaises(AttributeError, art._set_tags, None)
        art._set_tags("foo, bar")
        self.assertEqual(art.tags, ['bar', 'foo'])

    def test_created_short(self):
        """Test created_short method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_short(), "10 Oct, 2010")

    def test_created_rfc3339(self):
        """Test created_rfc3339 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_rfc3339(), "2010-10-10T11:10:10+0200")

    def test_created_rfc822(self):
        """Test created_rfc822 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_rfc822(),
                         "Sun, 10 Oct 2010 11:10:10 +0200")

    def test_created_detailed(self):
        """Test created_detailed method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_detailed(),
                         "Sunday, 10 Oct, 2010, 11:10:10")

    def test_get_short_body(self):
        """Test get_short_body method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)

        self.assertIn('<h2>Kiroku</h2>', art.get_short_body())
        self.assertIn('<p>Arcu', art.get_short_body())
        self.assertIn('<strong>Vestibulum</strong>', art.get_short_body())
        self.assertIn('aliquet.</p>', art.get_short_body())

        art_fname = os.path.join('articles', "full.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertNotEqual(art.get_short_body(), art.body)

        self.assertIn('<h2>Kiroku</h2>', art.get_short_body())
        self.assertIn('<p>Lorem', art.get_short_body())
        self.assertIn('elit.</p>', art.get_short_body())
        self.assertNotIn('<p>Arcu', art.get_short_body())

    def test__process_attrs(self):
        """Test _process_attrs method."""
        # Virtually the same as test_read tests. Nothing new to introduce.

    def test__set_title(self):
        """Test _set_title method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        self.assertEqual(art.title, None)
        art._set_title(None)
        self.assertEqual(art.title, None)
        art._set_title("")
        self.assertEqual(art.title, None)
        art._set_title("title")
        self.assertEqual(art.title, "title")

    def test_read(self):
        """Test read method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.body, "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.body, "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Arcu", art.body)
        self.assertIn("<strong>Vestibulum</strong>", art.body)
        self.assertIn("aliquet.</p>", art.body)
        self.assertNotIn("<!-- more -->", art.body)

        art_fname = os.path.join('articles', "full.rst")
        art = kiroku.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Lorem", art.body)
        self.assertIn("elit.</p>", art.body)
        self.assertIn("<!-- more -->", art.body)
        self.assertIn("leo.</p>", art.body)


class TestRss(unittest.TestCase):
    """Check Rss class"""

    def setUp(self):
        """Setup"""
        kiroku.CONFIG.update(kiroku.get_i18n_strings(gettext))
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        copytree(os.path.join(kiroku.DATA_DIR, "templates"), ".templates")

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)

    def test_initialization(self):
        """Test initialization"""
        rss = kiroku.Rss(kiroku.CONFIG)
        self.assertEqual(rss.items, [])

    def test_add(self):
        """Test add method"""
        rss = kiroku.Rss(kiroku.CONFIG)
        # pass wrong type - expected dict
        self.assertRaises(AttributeError, rss.add, "foo")
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
        rss = kiroku.Rss(kiroku.CONFIG)

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


class TestKiroku(unittest.TestCase):
    """Test Kiroku class"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        os.makedirs('articles/images')
        copytree(os.path.join(kiroku.DATA_DIR, "templates"), ".templates")

        # kiroku.ARTICLE_SHORT = ("*start* %(title)s\n%(tags)s\nurl_"
                                # "%(article_url)s\n%(short_body)s *end*")
        # kiroku.ARTICLE_TAG = "%(tag)s"
        # kiroku.HEADER = "<p>header1</p>"
        # kiroku.HEADLINE = "<p>%(title)s</p>"
        # kiroku.MAIN = "%(body)s"
        # kiroku.ARTICLE_HEADER = "<ah>%(title)s</ah>"
        # kiroku.ARTICLE_FOOTER = "<af>%(datetime)s</af>"
        # kiroku.TAG = "%(size)d\n%(tag)s\ntag_%(tag_url)s\n%(count)s\n"

        for fname, content in MOCK_ARTICLES.items():
            full_path = os.path.join('articles', fname)
            with open(full_path, "w") as fobj:
                fobj.write(content[0])
                os.utime(full_path, (content[1], content[1]))

        with open(".templates/main.html", "w") as fobj:
            fobj.write("%(body)s")
        with open(".templates/header.html", "w") as fobj:
            fobj.write("<p>header1</p>")
        with open(".templates/headline.html", "w") as fobj:
            fobj.write("<p>%(title)s</p>")
        with open(".templates/article_tag.html", "w") as fobj:
            fobj.write("<p>%(tag)s</p>")
        with open(".templates/tag.html", "w") as fobj:
            fobj.write("%(size)d\n%(tag)s\ntag_%(tag_url)s\n%(count)d")
        with open(".templates/article_short.html", "w") as fobj:
            fobj.write("*start* %(title)s\n%(tags)s\nurl_%(article_url)s"
                       "\n%(short_body)s *end*")
        with open(".templates/article_header.html", "w") as fobj:
            fobj.write("<ah>%(title)s</ah>")
        with open(".templates/article_footer.html", "w") as fobj:
            fobj.write("<af>%(datetime)s</af>")
        with open(".templates/favico.ico", "w") as fobj:
            fobj.write("")

        with open("favico.ico", "w") as fobj:
            fobj.write("")

        os.mkdir(".css")
        with open(".css/style.css", "w") as fobj:
            fobj.write('body {\n    background-color :  "olive" ;  \n}')

        os.mkdir(".js")

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)

    def test_initialization(self):
        """Test initialization of Kiroku object"""
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(rec.articles, [])
        self.assertEqual(rec.tags, {})
        self.assertEqual(rec.tag_cloud, None)
        self.assertEqual(rec._sorted_articles, [])
        self.assertEqual(rec._about_fname, None)

    def test__about(self):
        """Test _about method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(rec._about_fname, None)
        rec._about()

        rec._about_fname = "articles/about.rst"
        rec._about()
        self.assertTrue(os.path.exists("build/about.html"))
        with open("build/about.html") as fobj:
            self.assertIn("<p>Hi, my name is</p>", fobj.read())

    def test__archive(self):
        """Test _archive method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(rec._archive(), None)
        tags = {0: ["bar", "foo"],
                1: ["bar"],
                2: ["bar", "baz"],
                3: ["foo"],
                4: ["baz", "foo"],
                5: ["baz"],
                6: ["bar", "baz", "foo"]}
        fnames = {0: "zero",
                  1: "one",
                  2: "two",
                  3: "three",
                  4: "four",
                  5: "five",
                  6: "six"}

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read().strip(), "")

        for idx in range(3):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read().strip(), "")

        rec.articles = []
        for idx in range(6):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read().strip(), "<p>five</p>")

        rec.articles = []
        for idx in tags:
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            data = fobj.read().split(" ")
            self.assertEqual(len(data), 2, "Only two articles out of 7 "
                             "should be on archive page")
            self.assertEqual(data[0].strip(), "<p>five</p>")
            self.assertEqual(data[1].strip(), "<p>six</p>")

    def test__calculate_tag_cloud(self):
        """Test _calculate_tag_cloud method"""
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(rec.tag_cloud, None)
        rec._calculate_tag_cloud()
        self.assertEqual(rec.tag_cloud, "")

        rec.tag_cloud = "foo"
        rec._calculate_tag_cloud()
        self.assertEqual(rec.tag_cloud, "foo")

        rec.tag_cloud = None
        rec.tags = {'foo': ['a']}
        rec._calculate_tag_cloud()
        size, tag, tag_url, count = rec.tag_cloud.strip().split("\n")
        self.assertEqual(size, "9")
        self.assertEqual(tag_url, "tag_foo")
        self.assertEqual(tag, "foo")
        self.assertEqual(count, "1")

        rec.tag_cloud = None
        rec.tags = {'foo': ['a', 'b', 'c'], 'bar baz': ['a', 'f']}
        rec._calculate_tag_cloud()
        self.assertEqual(rec.tag_cloud,
                         '6\nbar baz\ntag_bar_baz\n2\n 9\nfoo\ntag_foo\n3\n')

    def test__harvest(self):
        """Test _harvest method"""
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec.read = lambda: None
        self.assertRaises(TypeError, rec._harvest, None)

        rec._harvest("articles/full.rst")
        self.assertEqual(rec.tags, {'blog': ['articles/full.rst']})

    def test__index(self):
        """Test _index method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(rec._index(), None)
        tags = {0: ["bar", "foo"],
                1: ["bar"],
                2: ["bar", "baz"],
                3: ["foo"],
                4: ["baz", "foo"],
                5: ["baz"],
                6: ["bar", "baz", "foo"]}
        fnames = {0: "zero",
                  1: "one",
                  2: "two",
                  3: "three",
                  4: "four",
                  5: "five",
                  6: "six"}

        with open("build/index.html") as fobj:
            self.assertEqual(fobj.read().strip(), "")

        for idx in range(3):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            art.body = fnames[idx]
            rec.articles.append(art)

        rec._index()

        self.assertEqual(len(rec.articles), 3)
        with open("build/index.html") as fobj:
            data = fobj.read()
            self.assertIn("url_zero.html", data)
            self.assertIn("url_one.html", data)
            self.assertIn("url_two.html", data)

        rec.articles = []
        for idx in range(6):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            art.body = "b%d" % idx
            rec.articles.append(art)

        rec._index()

        self.assertEqual(len(rec.articles), 6)
        with open("build/index.html") as fobj:
            data = fobj.read().split("*end*")
            data = [x for x in data if x.strip()]
            self.assertEqual(len(data), 5,
                             "Only five articles on the index page expected")

    def test__rss(self):
        """Test _rss method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)

        rec._rss()
        self.assertFalse(os.path.exists("build/rss.xml"))

        rec = kiroku.Kiroku(kiroku.CONFIG)
        for idx in range(1):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec._rss()
        with open("build/rss.xml") as fobj:
            xml = etree.fromstring(fobj.read())

        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 5)
        self.assertEqual(xml[0][4].tag, 'item')

        rec = kiroku.Kiroku(kiroku.CONFIG)
        # Create 11 records. Note, that record with guid l0 is oldest, and l10
        # is youngest record
        for idx in range(11):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("201010%d111010" % (idx + 1),
                                            "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec._rss()
        with open("build/rss.xml") as fobj:
            xml = etree.fromstring(fobj.read())

        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')

        channel = xml[0]
        items = channel.findall('item')
        # only 10 items shold be available.
        self.assertEqual(len(items), 10)

        first_item = items[0]
        self.assertEqual(first_item.find('pubDate').text,
                         'Mon, 11 Oct 2010 11:01:00 +0200')
        last_item = items[-1]
        self.assertEqual(last_item.find('pubDate').text,
                         'Tue, 19 Oct 2010 11:10:10 +0200')

    def test__save(self):
        """Test _save method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec._save()
        self.assertEqual(os.listdir("build"), [])

        for idx in range(3):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec._save()
        self.assertEqual(os.listdir("build"), ['l2', 'l1', 'l0'])

    def test__tag_pages(self):
        """Test _tag_pages method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec._tag_pages()
        self.assertEqual(os.listdir("build"), [])

        for idx in range(3):
            art = kiroku.Article(None, kiroku.CONFIG)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec.articles[0].tags = ['a', 'b']
        rec.articles[1].tags = ['c']
        rec.articles[2].tags = ['a', 'c']

        rec._tag_pages()
        self.assertEqual(sorted(os.listdir("build")),
                         ['tag-a.html', 'tag-b.html', 'tag-c.html'])

        title1, title2, title3 = ('<p>t0</p>', '<p>t1</p>', '<p>t2</p>')

        with open(os.path.join('build', 'tag-a.html')) as fobj:
            tag_res = fobj.read()
        self.assertIn(title1, tag_res)
        self.assertIn(title3, tag_res)
        self.assertNotIn(title2, tag_res)

        with open(os.path.join('build', 'tag-b.html')) as fobj:
            tag_res = fobj.read()
        self.assertIn(title1, tag_res)
        self.assertNotIn(title2, tag_res)
        self.assertNotIn(title3, tag_res)

        with open(os.path.join('build', 'tag-c.html')) as fobj:
            tag_res = fobj.read()
        self.assertNotIn(title1, tag_res)
        self.assertIn(title2, tag_res)
        self.assertIn(title3, tag_res)

    def test__walk(self):
        """Test _walk method"""
        rec = kiroku.Kiroku(kiroku.CONFIG)
        self.assertEqual(len(os.listdir("articles")), 7)
        self.assertTrue(rec._about_fname is None)

        # create additional file, with other extension than '.rst'
        with open(os.path.join("articles", "something.txt"), "w") as fobj:
            fobj.write("Hi!\n")
        self.assertEqual(len(os.listdir("articles")), 8)

        rec._walk()

        # so, we got one about page:
        self.assertFalse(rec._about_fname is None)
        # and 5 articles, even though there is "something.txt" (which is not
        # taken into an account), but also favico.ico.
        self.assertEqual(len(rec.articles), 5)

    def test_build(self):
        """Test build method. Basically this is entry point for other methods,
        and the only responsible for this method is to prepare build
        directory."""
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec.build()
        self.assertIn("css", os.listdir("build"))
        self.assertIn("js", os.listdir("build"))
        self.assertIn("images", os.listdir("build"))
        self.assertIn("index.html", os.listdir("build"))

        shutil.rmtree("build/js")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec.build()
        self.assertIn("css", os.listdir("build"))
        self.assertNotIn("js", os.listdir("build"))
        self.assertIn("images", os.listdir("build"))
        self.assertIn("index.html", os.listdir("build"))

        os.mkdir("articles/something_else")
        with open("articles/afile.txt", "w") as fobj:
            fobj.write("foo")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec.build()
        self.assertTrue(os.path.exists("build/something_else"))
        self.assertTrue(os.path.exists("build/afile.txt"))
        shutil.rmtree("build/something_else")
        os.unlink("build/afile.txt")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec.build()
        self.assertTrue(os.path.exists("build/something_else"))
        self.assertTrue(os.path.exists("build/afile.txt"))

    def test_update(self):
        """Dummy placeholder for update method"""

    def test__minify_css(self):
        """Test minify function for compressing CSS"""
        kiroku._minify_css(os.path.join(".css/style.css"))

    def test__create_json_data(self):
        """Test _create_json_data method"""
        os.mkdir("build")
        rec = kiroku.Kiroku(kiroku.CONFIG)
        rec._create_json_data()

        self.assertIn("search.json", os.listdir("build"))
        with open(os.path.join("build", "search.json")) as fobj:
            self.assertEqual(json.load(fobj),  {'a': [],
                                                'w': {}})

        art = kiroku.Article("foo.rst", kiroku.CONFIG)
        art.html_fname = "foo.html"
        art.body = "foo"
        art.title = "foo"
        art.tags = ['a', 'b']
        art.created = datetime.strptime("2000-12-12 12:05:00",
                                        "%Y-%m-%d %H:%M:%S")
        rec.articles = [art]

        art = kiroku.Article("bar.rst", kiroku.CONFIG)
        art.html_fname = "bar.html"
        art.body = "bar"
        art.title = "bar"
        art.tags = ['b', 'c']
        art.created = datetime.strptime("2000-12-12 12:05:00",
                                        "%Y-%m-%d %H:%M:%S")
        rec.articles.append(art)

        rec._create_json_data()
        with open(os.path.join("build", "search.json")) as fobj:
            json_data = json.load(fobj)
            json_data['a'] = [x.strip() for x in json_data['a']]
            self.assertEqual(json_data,
                             {'a': ['<p>foo</p>', '<p>bar</p>'],
                              'w': {'foo': [[0, 1]],
                                    'bar': [[1, 1]]}})


class TestFunctions(unittest.TestCase):
    """Test build and init functions"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)

        self._kiroku = kiroku.Kiroku
        kiroku.Kiroku = MockKiroku

    def tearDown(self):
        """Clean up"""
        kiroku.Kiroku = self._kiroku
        os.chdir(self._curdir)

    def test_build(self):
        """Test build funtion"""
        self.assertRaises(TypeError, kiroku.build)
        self.assertRaises(TypeError, kiroku.build, None)
        arg = MockArgParse()
        self.assertEqual(kiroku.build(arg, kiroku.CONFIG), 0)

    def test_init(self):
        """Test init funtion"""
        self.assertRaises(TypeError, kiroku.init)
        self.assertRaises(TypeError, kiroku.init, None)
        arg = MockArgParse()
        self.assertRaises(AttributeError, kiroku.init, arg, kiroku.CONFIG)
        arg.path = 'foo'
        self.assertEqual(kiroku.init(arg, kiroku.CONFIG), 0)


class TestFeedback(unittest.TestCase):
    """Test Feedback class"""
    def test(self):
        """Test Feedback behaviour"""

        class Interceptor:
            """simple class just to takeover the message"""
            msg = None

        def output_function(self, msg):
            """Store the message in the Interceptor class object"""
            Interceptor.msg = msg

        feedback = kiroku.Feedback("msg")
        self.assertEqual(kiroku.Feedback.output_function, None)
        self.assertEqual(feedback.output_function, None)
        self.assertEqual(Interceptor.msg, None)

        kiroku.Feedback.output_function = output_function

        feedback = kiroku.Feedback("msg")
        self.assertEqual(kiroku.Feedback.output_function, output_function)
        self.assertNotEqual(feedback.output_function, output_function)
        self.assertEqual(Interceptor.msg, "msg")

        kiroku.Feedback.output_function = None


if __name__ == '__main__':
    unittest.main()
