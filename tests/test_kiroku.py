#!/usr/bin/env python3
# encoding: utf-8
"""
Tests for reStructuredText translator and writer
"""
import unittest
import os
import time
from shutil import rmtree
from tempfile import mkdtemp
from datetime import datetime, timedelta
import locale

from xml.etree import ElementTree as etree

# For test purposes use C locale (defaults to English)
locale.setlocale(locale.LC_ALL, 'C')

import kiroku


MOCK_ARTICLES = {'empty.rst': ('', int(time.mktime((2010, 10, 10, 10, 10, 10,
                                                    0, 0, 0)))),
                 'complete.rst': (':Title: Kiroku\n:Datetime: 2013-09-08'
                 ' 10:57:24\n:Modified:\n:Tags: blog\n\nKiroku\n-------\n\n'
                 'Arcu scelerisque aliquam. Nullam viverra magna vitae leo. '
                 '**Vestibulum** in lacus sit amet lectus tempus aliquet.',
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
                 'full.rst': (':Title: Kiroku\n:Datetime: 2013-09-08'
                 ' 10:57:24\n:Modified:\n:Tags: blog\n\nKiroku\n-------\n\n'
                 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n\n'
                 '.. more\n\nArcu scelerisque aliquam. Nullam viverra magna '
                 'vitae leo. ', int(time.mktime((2005, 5, 5, 5, 5, 5, 0, 0,
                                                 0))))}


class TestArticle(unittest.TestCase):
    """Check Article class"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
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
        art = kiroku.Article(art_fname)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

        art_fname = os.path.join('articles', "minimal.rst")
        art = kiroku.Article(art_fname)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

    def test__transfrom_to_html(self):
        """Test _transfrom_to_html method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        html, attrs = art._transfrom_to_html()
        self.assertEqual(attrs, {})
        self.assertEqual(html, '')

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname)
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
        art = kiroku.Article(art_fname)
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
        art = kiroku.Article(None)
        self.assertRaises(AttributeError, art._set_html_name)

        art = kiroku.Article("foobar")
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = kiroku.Article("foobar?")
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = kiroku.Article("~fo'o'bar. Oto smok!!!.txt")
        art._set_html_name()
        self.assertEqual(art.html_fname, "fo-o-bar-Oto-smok.html")

        art = kiroku.Article("\\who is using such silly names?."
                             " żółty smok%.article")
        art._set_html_name()
        self.assertEqual(art.html_fname,
                         "who-is-using-such-silly-names-zolty-smok.html")

        art = kiroku.Article("2000-04-01_This is a joke.rst")
        art._set_html_name()
        self.assertEqual(art.html_fname, "This-is-a-joke.html")


    def test__set_ctime(self):
        """Test _set_ctime method"""
        # if no file is passed to the Article constructor, trying to open None
        # object as an argument for open() function will cause exception
        art = kiroku.Article(None)
        self.assertRaises(TypeError, art._set_ctime)

        # Try to caclulate creation time with the file mtime
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art._set_ctime()
        self.assertEqual(art.created,
                         datetime.strptime("20101010111010", "%Y%m%d%H%M%S"))

        # Process field 'datetime' as an Article creation time
        art = kiroku.Article(None)
        art._set_ctime('1998-07-06 21:12:21')
        self.assertEqual(art.created,
                         datetime.strptime("19980706211221", "%Y%m%d%H%M%S"))

    def test__set_tags(self):
        """Test _set_tags method"""
        art = kiroku.Article(None)
        self.assertRaises(AttributeError, art._set_tags, None)
        art._set_tags("foo, bar")
        self.assertEqual(art.tags, ['bar', 'foo'])

    def test_created_short(self):
        """Test created_short method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.created_short(), "10 Oct, 2010")

    def test_created_rfc3339(self):
        """Test created_rfc3339 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.created_rfc3339(), "2010-10-10T11:10:10+0200")

    def test_created_rfc822(self):
        """Test created_rfc822 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.created_rfc822(),
                         "Sun, 10 Oct 2010 11:10:10 +0200")

    def test_created_detailed(self):
        """Test created_detailed method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.created_detailed(),
                         "Sunday, 10 Oct, 2010, 11:10:10")

    def test_get_short_body(self):
        """Test get_short_body method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)

        self.assertIn('<h2>Kiroku</h2>', art.get_short_body())
        self.assertIn('<p>Arcu', art.get_short_body())
        self.assertIn('<strong>Vestibulum</strong>', art.get_short_body())
        self.assertIn('aliquet.</p>', art.get_short_body())

        art_fname = os.path.join('articles', "full.rst")
        art = kiroku.Article(art_fname)
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
        art = kiroku.Article(art_fname)
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
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.body, "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertEqual(art.body, "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Arcu", art.body)
        self.assertIn("<strong>Vestibulum</strong>", art.body)
        self.assertIn("aliquet.</p>", art.body)
        self.assertNotIn("<!-- more -->", art.body)

        art_fname = os.path.join('articles', "full.rst")
        art = kiroku.Article(art_fname)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Lorem", art.body)
        self.assertIn("elit.</p>", art.body)
        self.assertIn("<!-- more -->", art.body)
        self.assertIn("leo.</p>", art.body)


class TestRss(unittest.TestCase):
    """Check Rss class"""

    def test_initialization(self):
        """Test initialization"""
        rss = kiroku.Rss()
        self.assertEqual(rss.items, [])

    def test_add(self):
        """Test add method"""
        rss = kiroku.Rss()
        # pass wrong type - expected dict
        self.assertRaises(TypeError, rss.add, "foo")
        # pass wrong argument - expected dict containing title, link, desc and
        # date keys.
        self.assertRaises(KeyError, rss.add, {"foo": "bar"})

        rss.add({"title": "title",
                 "link": "foo.html",
                 "desc": "body",
                 "date": "2000"})

        self.assertEqual(len(rss.items), 1)

        xml = etree.fromstring(rss.items[0])
        self.assertEqual(len(xml), 5)
        self.assertEqual(xml.tag, 'item')
        self.assertEqual(xml[0].tag, 'title')
        self.assertEqual(xml[0].text, 'title')
        self.assertEqual(xml[1].tag, 'link')
        self.assertEqual(xml[1].text, 'foo.html')
        self.assertEqual(xml[2].tag, 'description')
        self.assertEqual(xml[2].text, 'body')
        self.assertEqual(xml[3].tag, 'pubDate')
        self.assertEqual(xml[3].text, '2000')
        self.assertEqual(xml[4].tag, 'guid')
        self.assertEqual(xml[4].text, 'foo.html')

        rss.add({"title": "title2",
                 "link": "foo2.html",
                 "desc": "<p>body2 - \"foo\"</p>",
                 "date": "2001"})
        self.assertEqual(len(rss.items), 2)

        xml = etree.fromstring(rss.items[1])
        self.assertEqual(len(xml), 5)
        self.assertEqual(xml.tag, 'item')
        self.assertEqual(xml[0].tag, 'title')
        self.assertEqual(xml[0].text, 'title2')
        self.assertEqual(xml[1].tag, 'link')
        self.assertEqual(xml[1].text, 'foo2.html')
        self.assertEqual(xml[2].tag, 'description')
        self.assertEqual(xml[2].text, '<p>body2 - "foo"</p>')
        self.assertEqual(xml[3].tag, 'pubDate')
        self.assertEqual(xml[3].text, '2001')
        self.assertEqual(xml[4].tag, 'guid')
        self.assertEqual(xml[4].text, 'foo2.html')

    def test_get(self):
        """Test get method"""
        rss = kiroku.Rss()

        xml = etree.fromstring(rss.get())
        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 4)
        self.assertEqual(xml[0].tag, 'channel')
        self.assertEqual(xml[0][0].tag, 'title')
        self.assertEqual(xml[0][0].text, 'Import that')
        self.assertEqual(xml[0][1].tag, 'link')
        self.assertEqual(xml[0][1].text, 'http://localhost')
        self.assertEqual(xml[0][2].tag, 'description')
        self.assertEqual(xml[0][2].text, 'Blog. Po prostu.')
        self.assertEqual(xml[0][3].tag, '{http://www.w3.org/2005/Atom}link')

        rss.add({"title": "title",
                 "link": "foo.html",
                 "desc": "body",
                 "date": "2000"})

        xml = etree.fromstring(rss.get())
        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 5)
        self.assertEqual(xml[0].tag, 'channel')
        self.assertEqual(xml[0][0].tag, 'title')
        self.assertEqual(xml[0][0].text, 'Import that')
        self.assertEqual(xml[0][1].tag, 'link')
        self.assertEqual(xml[0][1].text, 'http://localhost')
        self.assertEqual(xml[0][2].tag, 'description')
        self.assertEqual(xml[0][2].text, 'Blog. Po prostu.')
        self.assertEqual(xml[0][3].tag, '{http://www.w3.org/2005/Atom}link')
        self.assertEqual(xml[0][4].tag, 'item')
        self.assertEqual(len(xml[0][4]), 5)
        self.assertEqual(xml[0][4][0].tag, 'title')
        self.assertEqual(xml[0][4][0].text, 'title')
        self.assertEqual(xml[0][4][1].tag, 'link')
        self.assertEqual(xml[0][4][1].text, 'foo.html')
        self.assertEqual(xml[0][4][2].tag, 'description')
        self.assertEqual(xml[0][4][2].text, 'body')
        self.assertEqual(xml[0][4][3].tag, 'pubDate')
        self.assertEqual(xml[0][4][3].text, '2000')
        self.assertEqual(xml[0][4][4].tag, 'guid')
        self.assertEqual(xml[0][4][4].text, 'foo.html')


class TestKiroku(unittest.TestCase):
    """Test Kiroku class"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        os.makedirs('articles/images')

        for fname, content in MOCK_ARTICLES.items():
            full_path = os.path.join('articles', fname)
            with open(full_path, "w") as fobj:
                fobj.write(content[0])
                os.utime(full_path, (content[1], content[1]))

        os.mkdir(".templates")
        with open(".templates/main.html", "w") as fobj:
            fobj.write("%(body)s")
        with open(".templates/plain_header.html", "w") as fobj:
            fobj.write("<p>header1</p>")
        with open(".templates/headline.html", "w") as fobj:
            fobj.write("<p>%(title)s</p>")
        with open(".templates/article_tags.html", "w") as fobj:
            fobj.write("<p>tags</p>")
        with open(".templates/tag.html", "w") as fobj:
            fobj.write("%(size)d\n%(tag)s\ntag_%(tag_url)s\n%(count)d")
        with open(".templates/short_article.html", "w") as fobj:
            fobj.write("*start* %(title)s\n%(tags)s\nurl_%(article_url)s"
                       "\n%(short_body)s *end*")
        with open(".templates/article_header.html", "w") as fobj:
            fobj.write("<ah>%(title)s</ah>")
        with open(".templates/article_footer.html", "w") as fobj:
            fobj.write("<af>%(datetime)s</af>")
        with open(".templates/favico.ico", "w") as fobj:
            fobj.write("")

        os.mkdir(".css")
        with open(".css/style.css", "w") as fd:
            fd.write('body {\n    background-color :  "olive" ;  \n}')

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)

    def test_initialization(self):
        """Test initialization of Kiroku object"""
        rec = kiroku.Kiroku()
        self.assertEqual(rec.articles, [])
        self.assertEqual(rec.tags, {})
        self.assertEqual(rec.tag_cloud, None)
        self.assertEqual(rec.words, {})
        self.assertTrue(isinstance(rec.rss, kiroku.Rss))
        self.assertEqual(rec._sorted_articles, [])
        self.assertEqual(rec._about_fname, None)

    def test__about(self):
        """Test _about method"""
        os.mkdir("build")
        rec = kiroku.Kiroku()
        self.assertEqual(rec._about_fname, None)
        rec._about()

        rec._about_fname = "articles/about.rst"
        rec._about()
        self.assertTrue(os.path.exists("build/about.html"))
        with open("build/about.html") as fobj:
            self.assertIn( "<p>Hi, my name is</p>", fobj.read())

    def test__archive(self):
        """Test _archive method"""
        os.mkdir("build")
        rec = kiroku.Kiroku()
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
            self.assertEqual(fobj.read(), "\n")

        for idx in range(3):
            art = kiroku.Article(None)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read(), "\n")

        rec.articles = []
        for idx in range(6):
            art = kiroku.Article(None)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read(), "<p>five</p>\n\n")

        rec.articles = []
        for idx in tags:
            art = kiroku.Article(None)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            rec.articles.append(art)

        rec._archive()

        with open("build/archives.html") as fobj:
            self.assertEqual(fobj.read(), "<p>five</p>\n <p>six</p>\n\n")

    def test__calculate_tag_cloud(self):
        """Test _calculate_tag_cloud method"""
        rec = kiroku.Kiroku()
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
        self.assertEqual(tag, "foo")
        self.assertEqual(tag_url, "tag_foo")
        self.assertEqual(count, "1")

        rec.tag_cloud = None
        rec.tags = {'foo': ['a', 'b', 'c'], 'bar baz': ['a', 'f']}
        rec._calculate_tag_cloud()
        self.assertEqual(rec.tag_cloud,
                         '6\nbar baz\ntag_bar_baz\n2\n 9\nfoo\ntag_foo\n3\n')

    def test__harvest(self):
        """Test _harvest method"""
        rec = kiroku.Kiroku()
        rec.read = lambda: None
        self.assertRaises(TypeError, rec._harvest, None)

        rec._harvest("articles/full.rst")
        self.assertEqual(rec.tags, {'blog': ['articles/full.rst']})

    def test__index(self):
        """Test _index method"""
        os.mkdir("build")
        rec = kiroku.Kiroku()
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
            self.assertEqual(fobj.read(), "\n")

        for idx in range(3):
            art = kiroku.Article(None)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.tags = tags[idx]
            art.html_fname = fnames[idx] + ".html"
            art.title = fnames[idx]
            art.body = fnames[idx]
            rec.articles.append(art)

        rec._index()

        self.assertEqual(len(rec.articles), 3)
        with open("build/index.html") as fobj:
            self.assertEqual(fobj.read(),
                             '*start* zero\n<p>tags</p>, <p>tags</p>\n'
                             'url_zero.html\nzero *end*\n'
                             ' *start* one\n<p>tags</p>\n'
                             'url_one.html\none *end*\n'
                             ' *start* two\n<p>tags</p>, <p>tags</p>\n'
                             'url_two.html\ntwo *end*\n\n')

        rec.articles = []
        for idx in range(6):
            art = kiroku.Article(None)
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
            self.assertEqual(fobj.read(),
                             '*start* zero\n<p>tags</p>, <p>tags</p>\n'
                             'url_zero.html\nb0 *end*\n'
                             ' *start* one\n<p>tags</p>\n'
                             'url_one.html\nb1 *end*\n'
                             ' *start* two\n<p>tags</p>, <p>tags</p>\n'
                             'url_two.html\nb2 *end*\n'
                             ' *start* three\n<p>tags</p>\n'
                             'url_three.html\nb3 *end*\n'
                             ' *start* four\n<p>tags</p>, <p>tags</p>\n'
                             'url_four.html\nb4 *end*\n\n')

    def test__rss(self):
        """Test _rss method"""
        os.mkdir("build")
        rec = kiroku.Kiroku()

        rec._rss()
        self.assertEqual(rec.rss.items, [])

        rec = kiroku.Kiroku()
        for idx in range(1):
            art = kiroku.Article(None)
            art.created = datetime.strptime("20101010111010", "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec._rss()
        self.assertEqual(len(rec.rss.items), 1)

        with open("build/rss.xml") as fobj:
            xml = etree.fromstring(fobj.read())

        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')
        self.assertEqual(len(xml[0]), 5)
        self.assertEqual(xml[0][4].tag, 'item')

        rec = kiroku.Kiroku()
        # Create 11 records. Note, that record with guid l0 is oldest, and l10
        # is youngest record
        for idx in range(11):
            art = kiroku.Article(None)
            art.created = datetime.strptime("201010%d111010" % (idx + 1),
                                            "%Y%m%d%H%M%S")
            art.created += timedelta(idx)
            art.html_fname = "l%d" % idx
            art.title = "t%d" % idx
            art.body = "d%d" % idx
            rec.articles.append(art)

        rec._rss()
        self.assertEqual(len(rec.rss.items), 10)

        with open("build/rss.xml") as fobj:
            xml = etree.fromstring(fobj.read())

        self.assertEqual(len(xml), 1)
        self.assertEqual(xml.tag, 'rss')

        channel = xml[0]
        items = channel.findall('item')
        # only 10 <item> shold be available. It's hardcoded.
        # TODO: to be changed?
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
        rec = kiroku.Kiroku()
        rec._save()
        self.assertEqual(os.listdir("build"), [])

        for idx in range(3):
            art = kiroku.Article(None)
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
        rec = kiroku.Kiroku()
        rec._tag_pages()
        self.assertEqual(os.listdir("build"), [])

        for idx in range(3):
            art = kiroku.Article(None)
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

        t1, t2, t3 = ('<p>t0</p>', '<p>t1</p>', '<p>t2</p>')

        with open(os.path.join('build', 'tag-a.html')) as fd:
            tag_res = fd.read()
        self.assertIn(t1, tag_res)
        self.assertIn(t3, tag_res)
        self.assertNotIn(t2, tag_res)

        with open(os.path.join('build', 'tag-b.html')) as fd:
            tag_res = fd.read()
        self.assertIn(t1, tag_res)
        self.assertNotIn(t2, tag_res)
        self.assertNotIn(t3, tag_res)

        with open(os.path.join('build', 'tag-c.html')) as fd:
            tag_res = fd.read()
        self.assertNotIn(t1, tag_res)
        self.assertIn(t2, tag_res)
        self.assertIn(t3, tag_res)

    def test__walk(self):
        """Test _walk method"""
        rec = kiroku.Kiroku()
        self.assertEqual(len(os.listdir("articles")), 7)
        self.assertTrue(rec._about_fname is None)

        # create additional file, with other extension than '.rst'
        with open(os.path.join("articles", "something.txt"), "w") as fd:
            fd.write("Hi!\n")
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
        rec = kiroku.Kiroku()
        rec.build()
        self.assertIn("css", os.listdir("build"))
        self.assertIn("images", os.listdir("build"))
        self.assertIn("index.html", os.listdir("build"))

    def test_update(self):
        """Dummy placeholder for update method"""

    def test__minify_css(self):
        """Test minify function for compressing CSS"""
        kiroku._minify_css(os.path.join(".css/style.css"))



if __name__ == '__main__':
        unittest.main()
