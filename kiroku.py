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


from rest import blogArticleString
from naive_tzinfo import get_rfc3339, get_rfc822


SITE = "localhost"
LOCALE = locale.getlocale()[0]

FILENAME = re.compile("\d{4}-\d{2}-\d{2}_(.*).rst")
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
            ord("Ż"): "Z"}

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

ATOM_MAIN = """\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <author>gryf</author>
    <title>Import that</title>
    <updated>%(updated)s</updated>
    <id>http://vimja.com/</id>
    %(items)s
</feed>
"""
ATOM_ITEM = """
    <entry>
        <title>%(title)s</title>
        <link href="%(link)s"/>
        <content type="html">%(desc)s</content>
    </entry>
"""


def build(args):
    """Build the site"""
    if not (os.path.exists("manage.py") and os.path.islink("manage.py")):
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

    os.symlink(os.path.join(items_path, "kiroku.py"), "manage.py")
    sys.stdout.write('…all done.\n')
    return 0


def _trans(string):
    """translate string to remove accented letters"""
    return string.translate(TR_TABLE)


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


class RSS:
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

    def _rss(self):
        """Generate RSS 2.0 structured XML"""

    def get(self):
        """Return RSS XML string"""

        return RSS_MAIN % {"url": "http://%s" % SITE,
                           "items": "\n".join(self.items),
                           "site": SITE}


class Article:
    """Represents article"""
    def __init__(self, title, body=None, created=None):
        """Create the obj"""
        self.body = body
        self.created = created
        self.title = title

        self.fname = None
        self.html_fname = None
        self.tags = []

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

    def human_updated(self):
        """Return human updated date"""
        pass

    def _human_date(self):
        """Return human date"""
        pass


class Kiroku:
    """
    The Recorder. He should have all the information to be able to render the
    blog/portal/website correctly.
    """

    def __init__(self):
        self.articles = []
        self.tags = defaultdict(list)
        self.tag_cloud = {}
        self.words = {}
        self.rss = RSS()
        # if os.stat(".db.sqlite").st_size == 0:
            # self._create_schema()
        self._sorted_articles = []
        self._about_fname = None

    def build(self):
        """Convert articles against the template to build directory"""
        if not os.path.exists("build"):
            os.mkdir("build")
            os.mkdir("build/images")
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
            short_body = art.body.split("<!-- more -->")[0]
            self.rss.add({"title": art.title,
                          "link": "http://%s/%s" % (SITE, art.html_fname),
                          "date": art.created_rfc822(),
                          "desc": short_body})

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

            match = FILENAME.match(art.fname)
            if match:
                # remove the prepending dates out of filename
                art.html_fname = match.groups()[0].replace("_", "-") + ".html"
            else:
                # default
                art.html_fname = art.fname[:-4] + ".html"

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
        arts = os.listdir("articles")
        # convention. maybe we will sort them out by the creation date
        arts.sort()

        for fname in arts:
            if not fname.endswith(".rst"):
                continue
            if fname == "about.rst":
                self._about_fname = fname
            else:
                self._harvest(fname)

        self.articles = sorted(self.articles, key=attrgetter('created'),
                               reverse=True)

    def _about(self):
        """Save special page "about" """
        if not self._about_fname:
            return

        with open(os.path.join("articles", self._about_fname)) as fobj:
            html, dummy = blogArticleString(fobj.read())

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
        with open(os.path.join("articles", fname)) as fobj:
            html, attrs = blogArticleString(fobj.read())

        art = Article(attrs['title'], html, attrs.get('datetime'))
        if attrs.get('datetime'):
            art.created = datetime.strptime(attrs.get('datetime'),
                                            "%Y-%m-%d %H:%M:%S")
        else:
            mtime = os.stat(os.path.join("articles", fname)).st_mtime
            art.created = datetime.fromtimestamp(mtime)
        art.fname = fname
        tags = []
        if attrs.get('tags'):
            for tag in attrs.get('tags').split(","):
                tag = tag.strip()
                tags.append(tag)
                self.tags[tag].append(fname)
        art.tags = tags
        self.articles.append(art)

    def _calculate_tag_cloud(self):
        """Calculate tag cloud."""
        if self.tag_cloud:
            return self.tag_cloud

        anchor = _get_template("tag")

        tags = {}
        biggest = 0

        for tag in self.tags:
            tags[tag] = len(self.tags[tag])
            biggest = tags[tag] if tags[tag] > biggest else biggest

        low = 1
        high = 9

        for tag in self.tags:
            if log(biggest):
                size = (log(tags[tag]) / log(biggest)) * (high - low) + low
            else:
                size = 9
            self.tag_cloud[tag] = size

        tag_cloud = []
        for key in sorted(self.tags):
            tag_cloud.append(anchor % {"size": self.tag_cloud[key],
                                       "tag": key,
                                       "tag_url": _trans(key),
                                       "count": tags[key]})

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
