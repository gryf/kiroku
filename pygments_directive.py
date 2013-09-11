"""
Register pygments code highlighter in old-fashioned way; HTML produced by it
will have short css class names, and main "highlight" class by default for
pre tags.
"""

from docutils import nodes
from docutils.parsers.rst import directives, Directive

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter


def register(cssclass=None):
    """Overwrite specified directives with new Pygments class"""
    if cssclass:
        Pygments.cssclass = cssclass
    directives.register_directive('sourcecode', Pygments)
    directives.register_directive('code', Pygments)
    directives.register_directive('code-block', Pygments)


def _positive_int_or_1(argument):
    """
    Converts the argument into an integer. Returns positive integer. In
    case of integers smaller than 1, returns 1. In case of None, returns
    1.
    """
    if argument is None:
        return 1

    retval = 1
    try:
        retval = int(argument)
    except ValueError:
        pass

    if retval < 1:
        return 1

    return retval


class Pygments(Directive):
    """
    Source code syntax highlighting. Although since docutils-0.9 there is
    pygents highlighted code blocks, it was implemented not as expected -
    output of specific CSS classes differ from those, which can be
    generated using pygmentize command line tool.
    """
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged,
                   'number-lines': _positive_int_or_1}

    has_content = True
    cssclass = None

    def run(self):
        self.assert_has_content()
        if self.arguments:
            lexer = get_lexer_by_name(self.arguments[0])
        else:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()

        # take an arbitrary option if more than one is given
        kwargs = {'full': False,
                  'noclasses': False}

        if self.options and 'number-lines' in self.options:
            kwargs['linenos'] = 'inline'
            kwargs['linenostart'] = self.options['number-lines']

        if Pygments.cssclass:
            kwargs['cssclass'] = Pygments.cssclass

        if self.options and 'class' in self.options:
            kwargs['cssclass'] = self.options['class']

        formatter = HtmlFormatter(**kwargs)

        parsed = highlight('\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]
