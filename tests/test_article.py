#!/usr/bin/env python3
"""
Tests for article module
"""
from copy import deepcopy
from datetime import datetime
from gettext import gettext
from shutil import rmtree
from tempfile import mkdtemp
import os
import time
import unittest

from kiroku import kiroku
from kiroku import article


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


class TestArticle(unittest.TestCase):
    """Check Article class"""

    def setUp(self):
        """Assumption is, that all operations are performed in current
        directory with hardcoded article directory"""
        self._config = deepcopy(kiroku.CONFIG)
        kiroku.CONFIG['locale'] = 'C'
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
        kiroku.CONFIG = deepcopy(self._config)

    def test_initialization(self):
        """Tests initialization of the article"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

        art_fname = os.path.join('articles', "minimal.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        self.assertEqual(art.body, None)
        self.assertEqual(art.created, None)
        self.assertEqual(art._fname, art_fname)
        self.assertEqual(art.html_fname, None)
        self.assertEqual(art.tags, [])
        self.assertEqual(art.title, None)

    def test__transfrom_to_html(self):
        """Test _transfrom_to_html method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        html, attrs = art._transfrom_to_html()
        self.assertEqual(attrs, {})
        self.assertEqual(html, '')

        art_fname = os.path.join('articles', "complete.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
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
        art = article.Article(art_fname, kiroku.CONFIG)
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
        art = article.Article(None, kiroku.CONFIG)
        self.assertRaises(AttributeError, art._set_html_name)

        art = article.Article("foobar", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = article.Article("foobar?", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "foobar.html")

        art = article.Article("~fo'o'bar. Oto smok!!!.txt", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "fo-o-bar-Oto-smok.html")

        art = article.Article("\\who is using such silly names?."
                             " żółty smok%.article", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname,
                         "who-is-using-such-silly-names-zolty-smok.html")

        art = article.Article("2000-04-01_This is a joke.rst", kiroku.CONFIG)
        art._set_html_name()
        self.assertEqual(art.html_fname, "This-is-a-joke.html", kiroku.CONFIG)

    def test__set_ctime(self):
        """Test _set_ctime method"""
        # if no file is passed to the Article constructor, trying to open None
        # object as an argument for open() function will cause exception
        art = article.Article(None, kiroku.CONFIG)
        self.assertRaises(TypeError, art._set_ctime)

        # Try to caclulate creation time with the file mtime
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art._set_ctime()
        self.assertEqual(art.created,
                         datetime.strptime("20101010111010", "%Y%m%d%H%M%S"))

        # Process field 'datetime' as an Article creation time
        art = article.Article(None, kiroku.CONFIG)
        art._set_ctime('1998-07-06 21:12:21')
        self.assertEqual(art.created,
                         datetime.strptime("19980706211221", "%Y%m%d%H%M%S"))

    def test__set_tags(self):
        """Test _set_tags method"""
        art = article.Article(None, kiroku.CONFIG)
        self.assertRaises(AttributeError, art._set_tags, None)
        art._set_tags("foo, bar")
        self.assertEqual(art.tags, ['bar', 'foo'])

    def test_created_short(self):
        """Test created_short method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_short(), "10 Oct, 2010")

    def test_created_rfc3339(self):
        """Test created_rfc3339 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_rfc3339(), "2010-10-10T11:10:10+0000")

    def test_created_rfc822(self):
        """Test created_rfc822 method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_rfc822(),
                         "Sun, 10 Oct 2010 11:10:10 +0000")

    def test_created_detailed(self):
        """Test created_detailed method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.created_detailed(),
                         "Sunday, 10 Oct, 2010, 11:10:10")

    def test_get_short_body(self):
        """Test get_short_body method"""
        art_fname = os.path.join('articles', "empty.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)
        self.assertEqual(art.get_short_body(), "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.get_short_body(), art.body)

        self.assertIn('<h2>Kiroku</h2>', art.get_short_body())
        self.assertIn('<p>Arcu', art.get_short_body())
        self.assertIn('<strong>Vestibulum</strong>', art.get_short_body())
        self.assertIn('aliquet.</p>', art.get_short_body())

        art_fname = os.path.join('articles', "full.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
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
        art = article.Article(art_fname, kiroku.CONFIG)
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
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.body, "")

        art_fname = os.path.join('articles', "incomplete.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertEqual(art.body, "<p>body, body</p>")

        art_fname = os.path.join('articles', "complete.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Arcu", art.body)
        self.assertIn("<strong>Vestibulum</strong>", art.body)
        self.assertIn("aliquet.</p>", art.body)
        self.assertNotIn("<!-- more -->", art.body)

        art_fname = os.path.join('articles', "full.rst")
        art = article.Article(art_fname, kiroku.CONFIG)
        art.read()
        self.assertIn("<h2>Kiroku</h2>", art.body)
        self.assertIn("<p>Lorem", art.body)
        self.assertIn("elit.</p>", art.body)
        self.assertIn("<!-- more -->", art.body)
        self.assertIn("leo.</p>", art.body)


if __name__ == '__main__':
    unittest.main()
