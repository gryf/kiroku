#!/usr/bin/env python3
"""
Tests for reStructuredText translator and writer
"""
import locale
import unittest

from docutils import nodes

from kiroku import rest


class Mock(object):
    """Simple class for creating mocks"""


class MockDocument(object):
    """Mock the document"""
    def __init__(self):
        self.settings = Mock()
        self.settings.language_code = "en_US.UTF-8"
        self.settings.xml_declaration = None
        self.settings.stylesheet_path = None
        self.settings.stylesheet = None
        self.settings.initial_header_level = 1
        self.settings.math_output = "a b"
        self.reporter = None

    def walkabout(self, visitor):
        """mock walkabout method"""
        return


class TestCustomHTMLTranslator(unittest.TestCase):
    """Check CustomHTMLTranslator class"""

    def setUp(self):
        """Setup"""
        locale.setlocale(locale.LC_ALL, 'en_US.utf-8')
        self.doc = MockDocument()

    def tearDown(self):
        rest.BlogArticle.ATTRS = {}

    def test_initialization(self):
        """Tests initialization of the translator"""
        translator = rest.CustomHTMLTranslator(self.doc)
        self.assertEqual(translator.initial_header_level, 2)
        self.assertEqual(translator.head, [])
        self.assertEqual(translator.meta, [])
        self.assertEqual(translator.head_prefix, ['', '', '', '', ''])
        self.assertEqual(translator.body_prefix, [])
        self.assertEqual(translator.body_suffix, [])
        self.assertEqual(translator.stylesheet, [])
        self.assertEqual(translator.generator, (''))

    def test_visit_section(self):
        """Tests visit_section() method"""
        translator = rest.CustomHTMLTranslator(self.doc)
        translator.visit_section(None)
        self.assertEqual(translator.section_level, 1)
        translator.visit_section(None)
        self.assertEqual(translator.section_level, 2)

    def test_depart_section(self):
        """Tests depart_section() method"""
        translator = rest.CustomHTMLTranslator(self.doc)
        translator.section_level = 9
        translator.depart_section(None)
        self.assertEqual(translator.section_level, 8)
        translator.depart_section(None)
        self.assertEqual(translator.section_level, 7)

    def test_meta(self):
        """Tests visit_meta and depart_meta methods"""
        translator = rest.CustomHTMLTranslator(self.doc)
        meta_before = translator.meta
        translator.visit_meta(None)
        self.assertEqual(translator.meta, meta_before)

        meta_before = translator.meta
        translator.depart_meta(None)
        self.assertEqual(translator.meta, meta_before)

    def test_document(self):
        """Tests visit_document and depart_document methods"""
        translator = rest.CustomHTMLTranslator(self.doc)
        before = translator.head[:]
        translator.visit_document(None)

        self.assertEqual(translator.head, before)

        translator.depart_document(None)
        self.assertEqual(translator.head_prefix, ['', '', '', '', ''])

        self.assertEqual(translator.html_prolog, [])
        self.assertEqual(translator.meta, [])
        self.assertEqual(translator.head, [])
        self.assertEqual(translator.math_header, [])
        self.assertEqual(len(translator.html_head), 1)
        self.assertEqual(translator.body_prefix, [])
        self.assertEqual(translator.body_suffix, [])
        self.assertEqual(translator.fragment, [])
        self.assertEqual(translator.html_body, [])
        self.assertEqual(translator.context, [])

    def test_depart_docinfo(self):
        """Test depart_docinfo method. Should clean up body attribute without
        filling up docinfo attribute"""

        translator = rest.CustomHTMLTranslator(self.doc)
        translator.body.append("<some>tag</some>")
        self.assertEqual(translator.body, ["<some>tag</some>"])
        self.assertEqual(translator.docinfo, [])

        translator.depart_docinfo(None)
        self.assertEqual(translator.body, [])
        self.assertEqual(translator.docinfo, [])

    def test_visit_literal(self):
        """Test visit_literal method."""

        node = Mock()
        node.astext = lambda: "foo bar\n baz"
        node.get = lambda x, y: []

        translator = rest.CustomHTMLTranslator(self.doc)

        self.assertEqual(translator.body, [])
        self.assertRaises(nodes.SkipNode, translator.visit_literal, node)
        self.assertEqual(translator.body, ['<code>', 'foo', ' ', 'bar',
                                           '\n', ' ', 'baz', '</code>'])

        # case 2 - we have aan oprion like --list
        node = Mock()
        node.astext = lambda: "foo --list bar\n baz"
        node.get = lambda x, y: []

        translator = rest.CustomHTMLTranslator(self.doc)

        self.assertEqual(translator.body, [])
        self.assertRaises(nodes.SkipNode, translator.visit_literal, node)
        self.assertEqual(translator.body, ['<code>', 'foo', ' ',
                                           '<span class="pre">--list</span>',
                                           ' ', 'bar', '\n', ' ', 'baz',
                                           '</code>'])

        # case 3 - we have trailing spaces
        node = Mock()
        node.astext = lambda: "foo  "
        node.get = lambda x, y: []

        translator = rest.CustomHTMLTranslator(self.doc)

        self.assertEqual(translator.body, [])
        self.assertRaises(nodes.SkipNode, translator.visit_literal, node)
        self.assertEqual(translator.body, ['<code>', 'foo', '&nbsp; ',
                                           '</code>'])

    def test_visit_abbrv(self):
        """Test visit_abbreviation method."""

        node = Mock()
        node.children = [node]
        node.astext = lambda: "abbrv <abbreviation>"
        node.get = lambda x, y: []

        translator = rest.CustomHTMLTranslator(self.doc)

        self.assertEqual(translator.body, [])
        translator.visit_abbreviation(node)
        self.assertEqual(translator.body, ['<abbr '
                                           'title="abbreviation">'])

        node.astext = lambda: "abbrv"
        translator.body = []
        translator.visit_abbreviation(node)
        self.assertEqual(translator.body, ['<abbr>'])

    def test_visit_field(self):
        """Test visit_field method"""

        node = Mock()
        node2 = Mock()
        node.astext = lambda: "foo"
        node2.astext = lambda: "bar"

        translator = rest.CustomHTMLTranslator(self.doc)

        translator.visit_field([node, node2])
        self.assertEqual(translator.body, [])
        self.assertEqual(rest.BlogArticle.ATTRS, {'foo': 'bar'})


class TestBlogBodyWriter(unittest.TestCase):
    """Test BlogBodyWriter class"""

    def test_initialization(self):
        """Test BlogBodyWriter initialization"""
        writer = rest.BlogBodyWriter()
        self.assertEqual(writer.translator_class, rest.CustomHTMLTranslator)

    def test_translate(self):
        """Test translate method"""
        writer = rest.BlogBodyWriter()
        writer.document = MockDocument()
        writer.apply_template = lambda: "foo"  # don't read any template
        writer.translate()
        self.assertEqual(writer.output, "foo")


class TestBlogArticle(unittest.TestCase):
    """Test BlogArticle class"""

    def test_initialization(self):
        """Test BlogArticle initialization"""
        art = rest.BlogArticle("hello")
        self.assertEqual(art.rest_str, "hello")

    def test_publish(self):
        """Test translate method"""
        art = rest.BlogArticle("hello")
        self.assertEqual(art.publish(), ("<p>hello</p>", {}))

        art = rest.BlogArticle("hello\n\n.. more\n\nworld")
        self.assertEqual(art.publish(), ("<p>hello</p>\n\n<!-- more -->\n\n"
                                         "<p>world</p>", {}))

    def test__return_parsed_attrs(self):
        """Test _return_parsed_attrs method"""
        art = rest.BlogArticle(":tags: foo, bar")
        self.assertEqual(art.publish(), ("", {"tags": "foo, bar"}))

        art = rest.BlogArticle(":tags: foo, bar\n:data: some data\n:foo:")
        self.assertEqual(art.publish(), ("", {"tags": "foo, bar",
                                              "data": "some data"}))


if __name__ == '__main__':
    unittest.main()
