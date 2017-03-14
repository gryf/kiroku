"""
This module is responsible for conversion between reST and HTML with some
goods added.
"""
import imp
import re

from docutils import core
from docutils import nodes
from docutils.writers import html4css1

try:
    imp.find_module("pygments")
    SETTINGS = {'syntax_highlight': 'short'}
except ImportError:
    SETTINGS = {'syntax_highlight': 'none'}


class CustomHTMLTranslator(html4css1.HTMLTranslator):
    """
    Base class for reST files translations.
    There are couple of customizations for docinfo fields behaviour and
    abbreviations and acronyms.
    """
    def __init__(self, document):
        """
        Set some nice defaults for articles translations
        """
        html4css1.HTMLTranslator.__init__(self, document)
        self.initial_header_level = 2
        self.head = []
        self.meta = []
        self.head_prefix = ['', '', '', '', '']
        self.body_prefix = []
        self.body_suffix = []
        self.stylesheet = []
        self.generator = ('')

    def visit_section(self, node):
        """
        Don't affect document, just keep track of the section levels
        """
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    def visit_meta(self, node):
        pass

    def depart_meta(self, node):
        pass

    def visit_document(self, node):
        pass

    def depart_document(self, node):
        pass

    def depart_docinfo(self, node):
        """
        Reset body, remove unnecessary content.
        """
        self.body = []

    def visit_literal(self, node):
        """
        This is almost the same as the original one from HTMLTranslator class.
        The only difference is in used HTML tag: it uses 'code' instead of
        'tt'
        """
        self.body.append(self.starttag(node, 'code', ''))
        text = node.astext()
        for token in self.words_and_spaces.findall(text):
            if token.strip():
                # Protect text like "--an-option" and the regular expression
                # ``[+]?(\d+(\.\d*)?|\.\d+)`` from bad line wrapping
                if self.sollbruchstelle.search(token):
                    self.body.append('<span class="pre">%s</span>'
                                     % self.encode(token))
                else:
                    self.body.append(self.encode(token))
            elif token in ('\n', ' '):
                # Allow breaks at whitespace:
                self.body.append(token)
            else:
                # Protect runs of multiple spaces; the last space can wrap:
                self.body.append('&nbsp;' * (len(token) - 1) + ' ')
        self.body.append('</code>')
        # Content already processed:
        raise nodes.SkipNode

    def visit_abbreviation(self, node):
        """
        Define missing abbr HTML tag
        """
        node_text = node.children[0].astext()
        node_text = node_text.replace('\n', ' ')
        patt = re.compile(r'^(.+)\s<(.+)>')

        if patt.match(node_text):
            node.children[0] = nodes.Text(patt.match(node_text).groups()[0])
            self.body.append(self.starttag(node, 'abbr', '', title=patt.
                                           match(node_text).groups()[1]))

        else:
            self.body.append(self.starttag(node, 'abbr', ''))

    def visit_field(self, node):
        """
        Harvest docinfo fields and store it in global dictionary.
        """
        key, val = [n.astext() for n in node]
        BlogArticle.ATTRS[key.lower()] = val.strip()


class BlogBodyWriter(html4css1.Writer):
    """
    Custom Writer class for generating HTML partial with the article
    """
    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = CustomHTMLTranslator

    def translate(self):
        self.document.settings.output_encoding = "utf-8"
        html4css1.Writer.translate(self)


class BlogArticle(object):
    """Returns partial HTML of the article, and attribute dictionary
    string argument is an article in reST"""

    ATTRS = {}

    def __init__(self, rest_str):
        """Initialize the objects"""
        BlogArticle.ATTRS = {}
        self.rest_str = rest_str

    def publish(self):
        """return items: the article attrs and the html itself"""
        html_output = core.publish_string(self.rest_str,
                                          writer=BlogBodyWriter(),
                                          settings_overrides=SETTINGS)
        html_output = html_output.decode("utf-8").strip()
        html_output = html_output.replace("<!-- more -->", "\n<!-- more -->\n")
        return html_output, self._return_parsed_attrs()

    def _return_parsed_attrs(self):
        """Get the dictionary of article attributes out of field list gathered
        by the CustomHTMLTranslator object"""
        attrs = {}
        for key, item in self.ATTRS.items():
            if item:
                attrs[key] = item
        return attrs
