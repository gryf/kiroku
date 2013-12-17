"""
Template - simple template mechanism for kiroku
"""
import re


class Template:
    """Simple class for cooking up partials out of the templates."""

    def __init__(self, config):
        """Initialize object"""
        self.templates = {}
        self._cfg = config

    def __call__(self, template_name, data):
        """Return string, out of the provided template intrepolated by the
        data and default strings from the config"""
        if template_name not in self.templates:
            self._read_template(template_name)

        return self._get_updated_template(self.templates[template_name], data)

    def _get_updated_template(self, template, data):
        """Return the template string interpolated by data and default strings
        from config. Data from data argument will overwrite the defaults."""
        _data = {}
        _data.update(self._cfg)
        data = _data.update(data)
        return template % _data

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
