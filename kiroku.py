#!/usr/bin/env python3
"""
Kiroku - Manage and create static website.

Kiroku (喜六, in the meaning of putting something into the record; writing
something) is a simple tool which helps out to generate a full blown static
site out of the a reST articles.
"""
import os
import sys
import shutil
import re
from datetime import datetime
from math import log
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import defaultdict
from operator import attrgetter
import locale
from configparser import ConfigParser

from rest import BlogArticle
from naive_tzinfo import get_rfc3339, get_rfc822


SITE = "localhost"
LOCALE = locale.getlocale()[0]

TR_TABLE = {ord("ą"): "a",
            ord("ć"): "c",
            ord("ę"): "e",
            ord("ł"): "l",
            ord("ń"): "n",
            ord("ó"): "o",
            ord("ś"): "s",
            ord("ź"): "z",
            ord("ż"): "z",
            ord("Ą"): "A",
            ord("Ć"): "C",
            ord("Ę"): "E",
            ord("Ł"): "L",
            ord("Ń"): "N",
            ord("Ó"): "O",
            ord("Ś"): "S",
            ord("Ź"): "Z",
            ord("Ż"): "Z",
            ord("'"): "_",
            ord("!"): "",
            ord('"'): "_",
            ord("#"): "",
            ord("$"): "",
            ord("%"): "",
            ord("&"): "and",
            ord("'"): "_",
            ord("("): "",
            ord(")"): "",
            ord("*"): "",
            ord("+"): "",
            ord(","): "",
            ord("."): "",
            ord("/"): "",
            ord(":"): "",
            ord(";"): "",
            ord("<"): "",
            ord("="): "",
            ord(">"): "",
            ord("?"): "",
            ord("@"): "",
            ord("["): "",
            ord("\\"): "",
            ord("]"): "",
            ord("^"): "",
            ord("`"): "",
            ord("{"): "",
            ord("|"): "",
            ord("}"): "",
            ord(" "): "_",
            ord("~"): ""}

RSS_MAIN = """\
<?xml version="1.0"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Import that</title>
    <link>%(url)s</link>
    <description>Blog. Po prostu.</description>
    <atom:link href="http://%(site)s/rss.xml" rel="self"
        type="application/rss+xml" />
    %(items)s
  </channel>
</rss>
"""
RSS_ITEM = """
    <item>
        <title>%(title)s</title>
        <link>%(link)s</link>
        <description><![CDATA[%(desc)s]]></description>
        <pubDate>%(date)s</pubDate>
        <guid>%(link)s</guid>
    </item>
"""


def build(args):
    """Build the site"""
    if not (os.path.exists("kiroku.py") and os.path.islink("kiroku.py")):
        return 10

    kiroku = Kiroku()
    kiroku.build()

    if not args.dir_or_path:
        return 0

    return 0


def init(args):
    """Initialize given directory with details"""

    if os.path.exists(args.path):
        sys.stderr.write("File or directory `%s' exists. Removing. You may "
                         "commit seppuku.\n" % args.path)
        shutil.rmtree(args.path)

    sys.stdout.write("Initializing `%s'…" % args.path)

    items_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

    os.mkdir(args.path)
    os.chdir(args.path)

    shutil.copytree(os.path.join(items_path, "articles"), "articles")
    shutil.copytree(os.path.join(items_path, "templates"), ".templates")
    shutil.copytree(os.path.join(items_path, "css"), ".css")

    os.symlink(os.path.join(items_path, "kiroku.py"), "kiroku.py")
    sys.stdout.write('…all done.\n')
    return 0


def _trans(string_):
    """translate string to remove accented letters"""
    return string_.translate(TR_TABLE)


def _minify_css(fname):
    """Minify CSS (destructive!)"""
    comments = re.compile('\/\*.*?\*\/')
    whitespace = re.compile('[\n\s\t][\n\s\t]+')
    space = re.compile('\s?([;:{},+>])\s?')

    with open(fname) as fobj:
        css = fobj.read()

    css = comments.sub("", css)
    css = whitespace.sub(" ", css)
    css = space.sub(r'\1', css)
    css = css.replace(";}", "}")

    with open(fname, "w") as fobj:
        fobj.write(css)


def _get_template(template_name, compress=False):
    """
    Return the template out of the template name - so it is the basename of
    the template file without the file extension.

    Note, that all html comments (<!-- -->) will be truncated.
    If compress is set to True all of trailing spaces will be removed out of
    the template (you can call it "minifying" html)
    """

    templ = []

    comments = re.compile("<!--.*?-->", re.DOTALL)

    with open(".templates/%s.html" % template_name) as fobj:
        content = fobj.read()

    content = re.sub(comments, "", content)

    for line in content.split("\n"):
        if not line:
            continue

        if compress:
            templ.append(line)
        else:
            templ.append(line + "\n")

    if compress:
        return " ".join(templ)
    else:
        return "".join(templ)


class Rss:
    """Rss representation class"""
    def __init__(self):
        """Initialize RSS container"""
        self.items = []

    def add(self, item):
        """Add rss item to the list. Parameter item is a dictionary which
        contains 4 keys with corresponding values:

            title - title of the article
            link - link to the article
            desc - secription/first paragraph of the article
            date - publish date in format "Sun, 29 Sep 2002 19:09:28 GMT"
        """
        self.items.append(RSS_ITEM % item)

    def get(self):
        """Return RSS XML string"""

        return RSS_MAIN % {"url": "http://%s" % SITE,
                           "items": "\n".join(self.items),
                           "site": SITE}


class Article:
    """Represents article"""

    def __init__(self, fname):
        """Create the obj"""
        self.body = None
        self.created = None
        self.html_fname = None
        self.tags = []
        self.title = None
        self._fname = fname

    def read(self):
        """Read article and transform to html"""
        html, attrs = self._transfrom_to_html()
        self.body = html
        self._process_attrs(attrs)
        self._set_html_name()

    def created_short(self):
        """Return human created date"""
        return self.created.strftime("%d %b, %Y")

    def created_detailed(self):
        """Return human created date"""
        return self.created.strftime("%A, %d %b, %Y, %X")

    def created_rfc3339(self):
        """Return RFC 3339 formatted date"""
        return get_rfc3339(self.created)

    def created_rfc822(self):
        """Return RFC 822 formatted date"""
        # RFC 822 doesn't allow localized strings
        locale.setlocale(locale.LC_ALL, "C")
        date = get_rfc822(self.created)
        locale.setlocale(locale.LC_ALL, LOCALE)
        return date

    def _transfrom_to_html(self):
        """Return processed article and its fileds"""
        html = attrs = None
        with open(self._fname) as fobj:
            html, attrs = BlogArticle(fobj.read()).publish()
        return html, attrs

    def _process_attrs(self, attrs):
        """Process provided article attributes"""
        action_map = {'datetime': self._set_ctime,
                      'tags': self._set_tags,
                      'title': self._set_title}

        for key in attrs:
            if action_map.get(key):
                action_map[key](attrs[key])

        if not self.created:
            self._set_ctime()

        if not self.title:
            self.title = self._fname

    def _set_ctime(self, date_str=None):
        """Set article creation time either with provided date_str, or via
        article files' mtime."""
        if date_str:
            self.created = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            mtime = os.stat(self._fname).st_mtime
            self.created = datetime.fromtimestamp(mtime)

    def _set_tags(self, tags_str):
        """Process tags into a list. List of tags is sorted in alphabetical
        order"""
        tags = []
        for tag in tags_str.split(","):
            tag = tag.strip()
            tags.append(tag)
        tags.sort()

        self.tags = tags

    def _set_title(self, title):
        """Set title out of provided title."""
        if title:
            self.title = title

    def _set_html_name(self):
        """Caclulate html uri part"""
        # Files are sometimes named:
        # YYYY-MM-DD_some_informative_name.rst
        re_fname = re.compile("\d{4}-\d{2}-\d{2}_(.*)")

        dummy, name = os.path.split(self._fname)
        name, dummy = os.path.splitext(name)

        name = _trans(name)

        match = re_fname.match(name)
        if match:
            # remove the prepending dates out of filename
            self.html_fname = match.groups()[0].replace("_", "-") + ".html"
        else:
            # default.
            name, dummy = os.path.splitext(name)
            name = name.replace("_", "-")
            self.html_fname = name + ".html"

    def get_short_body(self):
        """Return part of the HTML body up to first <!-- more --> comment"""
        return self.body.split("<!-- more -->")[0].strip()


class Kiroku:
    """
    The Recorder. He should have all the information to be able to render the
    blog/portal/website correctly.
    """

    def __init__(self):
        self.articles = []
        self.tags = defaultdict(list)
        self.tag_cloud = None
        self.words = {}
        self.rss = Rss()
        # if os.stat(".db.sqlite").st_size == 0:
            # self._create_schema()
        self._sorted_articles = []
        self._about_fname = None

    def build(self):
        """Convert articles against the template to build directory"""
        if not os.path.exists("build"):
            os.makedirs(os.path.join("build", "images"))
            shutil.copytree(".css", "build/css")
            _minify_css(os.path.join("build", "css", "style.css"))

        self._walk()
        self._calculate_tag_cloud()
        self._about()
        self._save()
        shutil.rmtree(os.path.join("build", "images"))
        shutil.copytree(os.path.join("articles", "images"),
                        os.path.join("build", "images"))
        shutil.copy(".templates/favico.ico", "build/images")
        self._tag_pages()
        self._index()
        self._archive()
        self._rss()

    def _rss(self):
        """Write rss.xml file"""
        for art in self.articles[:10]:
            self.rss.add({"title": art.title,
                          "link": "http://%s/%s" % (SITE, art.html_fname),
                          "date": art.created_rfc822(),
                          "desc": art.get_short_body()})

        with open(os.path.join("build", "rss.xml"), "w") as fobj:
            fobj.write(self.rss.get())

    def _tag_pages(self):
        """Create pages for the tag links"""
        main = _get_template("main")
        plain_header = _get_template("plain_header")
        headline = _get_template("headline")
        article_tags = _get_template("article_tags").strip()

        tags = defaultdict(list)
        for art in self.articles:
            for tag in art.tags:
                tags[tag].append(art)

        for tag in tags:
            titles = []
            for art in tags[tag]:
                art_tags = ", ".join([article_tags % {"tag_url": _trans(tag_),
                                                      "tag": tag_}
                                      for tag_ in art.tags])
                titles.append(headline % {"article_url": art.html_fname,
                                          "title": art.title,
                                          "datetime": art.created_rfc3339(),
                                          "human_date": art.created_short(),
                                          "tags": art_tags})

            with open(os.path.join("build", "tag-%s.html" % _trans(tag)),
                      "w") as fobj:
                header = plain_header % {"title": "Wpisy z etykietą: %s" %
                                         tag}

                fobj.write(main % {"page_header": "import that",
                                   "title": "Wpisy z etykietą: %s - " % tag,
                                   "site_name": SITE,
                                   "header": header,
                                   "body": " ".join(titles),
                                   "footer": "",
                                   "class_index": "current",
                                   "class_arch": "",
                                   "class_about": "",
                                   "tags": self.tag_cloud})

    def _index(self):
        """Create index.html for the main site entry"""
        main = _get_template("main")
        short_article = _get_template("short_article")
        article_tags = _get_template("article_tags").strip()

        titles = []
        for art in self.articles[:5]:
            short_body = art.body.split("<!-- more -->")[0]
            art_tags = ", ".join([article_tags %
                                  {"tag_url": _trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])
            titles.append(short_article % {"article_url": art.html_fname,
                                           "title": art.title,
                                           "datetime": art.created_rfc3339(),
                                           "human_date": art.created_short(),
                                           "short_body": short_body,
                                           "tags": art_tags})

        with open(os.path.join("build", "index.html"), "w") as fobj:

            fobj.write(main % {"page_header": "import that",
                               "title": "",
                               "site_name": SITE,
                               "header": "",
                               "body": " ".join(titles),
                               "footer": "",
                               "class_index": "current",
                               "class_arch": "",
                               "class_about": "",
                               "tags": self.tag_cloud})

    def _archive(self):
        """Create atchive.html for the site"""
        main = _get_template("main")
        plain_header = _get_template("plain_header")
        headline = _get_template("headline")
        article_tags = _get_template("article_tags").strip()

        titles = []
        for art in self.articles[5:]:
            art_tags = ", ".join([article_tags %
                                  {"tag_url": _trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])
            titles.append(headline % {"article_url": art.html_fname,
                                      "title": art.title,
                                      "datetime": art.created_rfc3339(),
                                      "human_date": art.created_short(),
                                      "tags": art_tags})

        with open(os.path.join("build", "archives.html"), "w") as fobj:
            header = plain_header % {"title": "Archiwum"}

            fobj.write(main % {"page_header": "import that",
                               "title": "Archiwum - ",
                               "site_name": SITE,
                               "header": header,
                               "body": " ".join(titles),
                               "footer": "",
                               "class_index": "",
                               "class_arch": "current",
                               "class_about": "",
                               "tags": self.tag_cloud})

    def _save(self):
        """
        Save articles and other generated pages into html using the templates.

        There are following available templates:
            main.html - main page skeleton
            tag.html - snippet for tag cloud entry
            article_header.html - article first heading and the datetime info
            article_footer.html - article tags, time, and author (maybe)

        Template have following pieces available to be filled.
        main:
            title - title of the page/ first header
            page_header - visible as the second part of the page and as a
                          main title of the page/blog (the biggest h1)
            header - article_header
            body - body of the page. Typically it is a
            footer - article_footer

            tags - tag cloud as a links for apropriate pages

        article_header:
            title - ideally the same as in main template
            datetime
            human_date - Those two are the very same date with possibly
                         different formats - first is the simply RFC 3339
                         formatted date the second is its human readable form

        tag:
            tag - tag name
            count - tag count across the articles
            size - number representing the size of the tag from range 1-9


        """
        main = _get_template("main")
        article_header = _get_template("article_header")
        article_footer = _get_template("article_footer")
        article_tags = _get_template("article_tags").strip()

        for art in self.articles:

            art_tags = ", ".join([article_tags %
                                  {"tag_url": _trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])

            header = article_header % {"title": art.title,
                                       "datetime": art.created_rfc3339(),
                                       "human_date": art.created_short()}
            footer = article_footer % {'rfc_date': art.created_rfc3339(),
                                       "datetime": art.created_detailed(),
                                       "human_date": art.created_detailed(),
                                       "tags": art_tags}

            with open(os.path.join("build", art.html_fname), "w") as fobj:
                fobj.write(main % {"page_header": "import that",
                                   "title": art.title + " - ",
                                   "site_name": SITE,
                                   "header": header,
                                   "body": art.body,
                                   "footer": footer,
                                   "class_index": "current",
                                   "class_arch": "",
                                   "class_about": "",
                                   "tags": self.tag_cloud})

    def _walk(self):
        """Walk through the flat list of the articles and gather all of the
        goodies"""
        art_filenames = os.listdir("articles")
        # convention. maybe we will sort them out by the creation date
        art_filenames.sort()

        for fname in art_filenames:
            full_path = os.path.join("articles", fname)
            if not fname.endswith(".rst"):
                continue
            if fname == "about.rst":
                self._about_fname = full_path
            else:
                self._harvest(full_path)

        self.articles = sorted(self.articles, key=attrgetter('created'),
                               reverse=True)

    def _about(self):
        """Save special page "about" """
        if not self._about_fname:
            return

        with open(self._about_fname) as fobj:
            html, dummy = BlogArticle(fobj.read()).publish()

        main = _get_template("main")
        plain_header = _get_template("plain_header")

        header = plain_header % {"title": "O mnie"}

        with open(os.path.join("build", "about.html"), "w") as fobj:
            fobj.write(main % {"page_header": "import that",
                               "title": "O mnie" + " - ",
                               "site_name": SITE,
                               "header": header,
                               "body": html,
                               "footer": "",
                               "class_index": "",
                               "class_arch": "",
                               "class_about": "current",
                               "tags": self.tag_cloud})

    def _harvest(self, fname):
        """Gather all the necesary info for the article"""
        print("Processing `%s'" % fname)
        art = Article(fname)
        art.read()
        self.articles.append(art)

        for tag in art.tags:
            self.tags[tag].append(fname)

    def _calculate_tag_cloud(self):
        """Calculate tag cloud."""
        if self.tag_cloud:
            return self.tag_cloud

        self.tag_cloud = {}
        anchor = _get_template("tag")

        tag_wieght = {}
        biggest = 0

        for tag in self.tags:
            tag_wieght[tag] = len(self.tags[tag])
            biggest = tag_wieght[tag] if tag_wieght[tag] > biggest else biggest

        low = 1
        high = 9

        for tag in self.tags:
            if log(biggest):
                size = (log(tag_wieght[tag]) / log(biggest)) * \
                        (high - low) + low
            else:
                size = 9
            self.tag_cloud[tag] = size

        tag_cloud = []
        for key in sorted(self.tags):
            tag_cloud.append(anchor % {"size": self.tag_cloud[key],
                                       "tag": key,
                                       "tag_url": _trans(key),
                                       "count": tag_wieght[key]})

        self.tag_cloud = " ".join(tag_cloud)

    def update(self, path='articles', force=False):
        """Update the given path.
        If path is a file, such file would be refreshed"""


if __name__ == '__main__':
    PARSER = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)

    SUBPARSER = PARSER.add_subparsers()
    INIT = SUBPARSER.add_parser("init", help="Initilaize provided directory "
                                "with the defaults. If directory exists it "
                                "will be wiped out. You have been warned.")
    INIT.add_argument("path")
    INIT.set_defaults(func=init)

    BUILD = SUBPARSER.add_parser("build", help="Build entire site, or "
                                 "selected file. If no path is provided, "
                                 "default `articles' would be used to perform "
                                 "check for updates and then build if any of "
                                 "the articles has changed.")
    BUILD.add_argument("dir_or_path", nargs="?")
    BUILD.add_argument("-p", "--pretend", help="Don't do the action, just "
                       "give the info what would gonna to happen.",
                       action="store_true", default=False)
    BUILD.set_defaults(func=build)

    ARGS = PARSER.parse_args()

    CONF = ConfigParser()
    if CONF.read("config.ini") and 'kiroku' in CONF.sections():
        if CONF['kiroku'].get('server_name'):
            SITE = CONF['kiroku']['server_name']

        if CONF['kiroku'].get('locale', None):
            LOCALE = CONF['kiroku']['locale']

    locale.setlocale(locale.LC_ALL, LOCALE)

    sys.exit(ARGS.func(ARGS))
