#!/usr/bin/env python3
"""
Template - simple template mechanism for kiroku
"""
import re


class Template:
    """Simple class for template storage"""

    def __init__(self):
        """Initialize object"""
        self.templates = {}

    def __call__(self, template_name):
        """Get the template"""
        if template_name not in self.templates:
            self._read_template(template_name)

        return self.templates[template_name]

    def _read_template(self, template_name):
        """
        Return the template out of the template name - so it is the basename
        of the template file without the file extension.

        Note, that all html comments (<!-- -->) will be truncated.
        If compress is set to True all of trailing spaces will be removed out
        of the template (you can call it "minifying" html)
        """

        templ = []
        comments = re.compile("<!--.*?-->", re.DOTALL)

        try:
            with open(".templates/%s.html" % template_name) as fobj:
                content = fobj.read()
        except IOError:
            with open(".templates/%s.xml" % template_name) as fobj:
                content = fobj.read()

        content = re.sub(comments, "", content)

        for line in content.split("\n"):
            if not line:
                continue
            templ.append(line + "\n")

        self.templates[template_name] = "".join(templ).strip()
