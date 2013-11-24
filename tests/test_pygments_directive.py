#!/usr/bin/env python3
# encoding: utf-8
"""
Tests for Pygments docutils directive
"""
import unittest

from docutils.parsers.rst import directives

from kiroku import pygments_directive


class TestPygmentsDirective(unittest.TestCase):
    """Check Pygments directive module"""

    def setUp(self):
        """Setup"""
        try:
            directives._directives['code'].cssclass = None
        except KeyError:
            pass
        directives._directives = {}

    def test_register(self):
        """Tests registering directive"""
        self.assertEqual(directives._directives, {})
        pygments_directive.register()
        self.assertEqual(directives._directives,
                         {'code': pygments_directive.Pygments,
                          'code-block': pygments_directive.Pygments,
                          'sourcecode': pygments_directive.Pygments})

        self.assertEqual(directives._directives['code'].cssclass, None)

        directives._directives = {}
        pygments_directive.register("some-code-css-class")
        self.assertEqual(directives._directives,
                         {'code': pygments_directive.Pygments,
                          'code-block': pygments_directive.Pygments,
                          'sourcecode': pygments_directive.Pygments})
        self.assertEqual(directives._directives['code'].cssclass,
                         "some-code-css-class")

    def test_positive_int_or_1(self):
        """Test conversion of the directive argument - used for numbering
        lines"""

        self.assertEqual(pygments_directive._positive_int_or_1(0), 1)
        self.assertEqual(pygments_directive._positive_int_or_1(1), 1)
        self.assertEqual(pygments_directive._positive_int_or_1(2), 2)
        self.assertEqual(pygments_directive._positive_int_or_1("0"), 1)
        self.assertEqual(pygments_directive._positive_int_or_1("1"), 1)
        self.assertEqual(pygments_directive._positive_int_or_1("2"), 2)
        self.assertEqual(pygments_directive._positive_int_or_1(10.0), 10)
        self.assertEqual(pygments_directive._positive_int_or_1("10.0"), 1)
        self.assertEqual(pygments_directive._positive_int_or_1(None), 1)
        self.assertEqual(pygments_directive._positive_int_or_1("5"), 5)
        self.assertEqual(pygments_directive._positive_int_or_1("bullshit"), 1)
        self.assertEqual(pygments_directive._positive_int_or_1("-1"), 1)
        self.assertEqual(pygments_directive._positive_int_or_1("-10"), 1)

        # Yup, it will fail if passed complex. However, all we are going to
        # get is string so..
        self.assertRaises(TypeError, pygments_directive._positive_int_or_1,
                          2j, 1)
        self.assertEqual(pygments_directive._positive_int_or_1("2j"), 1)

    def test_pygments_directive_run(self):
        """Test run() method of Pygments directive class"""
        # init(self, name, arguments, options, content, lineno,
        #      content_offset, block_text, state, state_machine)
        pyg = pygments_directive.Pygments('code', [], {}, ["hello world!"], 1,
                                          0, "foo bar hello world!", None,
                                          None)
        result = pyg.run()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.astext(), ('<div class="highlight"><pre>'
                                           'hello world!\n</pre></div>\n'))

        pyg = pygments_directive.Pygments('code', ['python'], {},
                                          ["print(\"hello world!\")"], 1,
                                          0, "foo bar hello world!", None,
                                          None)
        result = pyg.run()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.astext(),
                         ('<div class="highlight"><pre><span class="k">print'
                          '</span><span class="p">(</span><span class="s">'
                          '&quot;hello world!&quot;</span><span class="p">)'
                          '</span>\n</pre></div>\n'))

        pyg = pygments_directive.Pygments('code', ['python'],
                                          {'number-lines': 2},
                                          ["print(\"hello world!\")"], 1,
                                          0, "foo bar hello world!", None,
                                          None)
        result = pyg.run()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.astext(),
                         ('<div class="highlight"><pre><span class="lineno">2'
                          '</span> <span class="k">print</span><span '
                          'class="p">(</span><span class="s">&quot;hello '
                          'world!&quot;</span><span class="p">)</span>'
                          '\n</pre></div>\n'))

        pygments_directive.register("custom")
        pyg = pygments_directive.Pygments('code', ['python'],
                                          {'number-lines': 2},
                                          ["print(\"hello world!\")"], 1,
                                          0, "foo bar hello world!", None,
                                          None)
        result = pyg.run()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.astext(),
                         ('<div class="custom"><pre><span class="lineno">2'
                          '</span> <span class="k">print</span><span '
                          'class="p">(</span><span class="s">&quot;hello '
                          'world!&quot;</span><span class="p">)</span>'
                          '\n</pre></div>\n'))

        pyg = pygments_directive.Pygments('code', ['python'],
                                          {'number-lines': 2,
                                           'class': 'a-class'},
                                          ["print(\"hello world!\")"], 1,
                                          0, "foo bar hello world!", None,
                                          None)
        result = pyg.run()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.astext(),
                         ('<div class="a-class"><pre><span class="lineno">2'
                          '</span> <span class="k">print</span><span '
                          'class="p">(</span><span class="s">&quot;hello '
                          'world!&quot;</span><span class="p">)</span>'
                          '\n</pre></div>\n'))


if __name__ == '__main__':
        unittest.main()
