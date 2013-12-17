#!/usr/bin/env python3
"""
Tests for template module
"""
from shutil import rmtree
from tempfile import mkdtemp
import os
import unittest

from kiroku import template


class TestTemplate(unittest.TestCase):
    """Test Template class"""

    def setUp(self):
        """Create some playground"""
        self._curdir = os.path.abspath(os.curdir)
        self._dir = mkdtemp()
        os.chdir(self._dir)
        os.makedirs('.templates')

        with open(".templates/foo.html", "w") as fobj:
            fobj.write("<span>foo</span>")
        with open(".templates/bar.xml", "w") as fobj:
            fobj.write('<?xml version="1.0"?>\n<bar>bar</bar>\n')
        with open(".templates/baz.html", "w") as fobj:
            fobj.write("\n\n\n   <p>baz</p>       \n  <!-- comment\n"
                       " comment 2nd line -->\n            \n\n")

    def tearDown(self):
        """Clean up"""
        os.chdir(self._curdir)
        rmtree(self._dir)

    def testInit(self):
        """Test Template initialization"""
        self.assertRaises(TypeError, template.Template)
        tpl = template.Template({})
        self.assertEqual(tpl.templates, {})

    def test_call(self):
        """Test __call__ method"""
        tpl = template.Template({})

        # not existing templates will raise an exception
        self.assertRaises(IOError, tpl, None, "no such file or directory")

        self.assertEqual(tpl('foo', {}), "<span>foo</span>")
        self.assertEqual(len(tpl.templates), 1)
        self.assertEqual(tpl.templates['foo'], "<span>foo</span>")

        self.assertEqual(tpl('bar', {}), '<?xml version="1.0"?>\n<bar>bar</bar>')
        self.assertEqual(len(tpl.templates), 2)

        self.assertEqual(tpl('baz', {}), '<p>baz</p>')
        self.assertEqual(len(tpl.templates), 3)

        def fake_read_tpl(self, name):
            """fake _read_template method"""
            raise Exception("Should never happen")

        tpl._read_template = fake_read_tpl
        # Now, get 'foo' template from cache, instead of reading it again
        self.assertEqual(tpl('foo', {}), "<span>foo</span>")
        self.assertEqual(len(tpl.templates), 3)

    def test_get_updated_template(self):
        """Test _get_updated_template method"""

        tpl = template.Template({})
        self.assertRaises(TypeError, tpl._get_updated_template)
        self.assertRaises(TypeError, tpl._get_updated_template, '')
        self.assertRaises(TypeError, tpl._get_updated_template, '', None)

        tpl = template.Template({})
        self.assertEqual(tpl._get_updated_template("blah", {}), "blah")
        self.assertRaises(KeyError, tpl._get_updated_template, "blah %(foo)s",
                          {})
        self.assertRaises(KeyError, tpl._get_updated_template,
                          "blah %(foo)s, %(bar)s",
                          {"foo": 1})

        # we have some defaults, and we passed some more values, than expected
        tpl = template.Template({"foo": 1})
        self.assertEqual(tpl._get_updated_template("blah %(foo)s",
                                                   {"foo": 1}),
                         "blah 1")
        self.assertEqual(tpl._get_updated_template("blah %(foo)s",
                                                   {"foo": 1, "burp": "pi"}),
                         "blah 1")

        # we have some defaults and it is not enough to fill the template,
        # unless provided some data as an argument
        tpl = template.Template({"bar": 2})
        self.assertEqual(tpl._get_updated_template("blah", {}), "blah")
        self.assertRaises(KeyError, tpl._get_updated_template, "blah %(foo)s",
                          {})
        self.assertEqual(tpl._get_updated_template("blah %(foo)s, %(bar)s",
                                                   {"foo": 1}),
                                                   "blah 1, 2")
        # data passed as argument overcomes the defaults
        self.assertEqual(tpl._get_updated_template("blah %(foo)s, %(bar)s",
                                                   {"foo": 1, "bar": 3}),
                                                   "blah 1, 3")


if __name__ == '__main__':
    unittest.main()
