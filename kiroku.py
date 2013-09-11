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

from rest import blogArticleString
from naive_tzinfo import get_rfc3339


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


def trans(string):
    """translate string to remove accented letters"""
    return string.translate(TR_TABLE)


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
        sys.stderr.write("File or directory `%s' exists. Removing. Now commit"
                         " seppuku.\n" % args.path)
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


def _get_template(template_name, compress=False):
    """
    Return the template out of the template name - so it is the basename of
    the template file without the file extension.

    Note, that all html comments (<!-- -->) will be truncated.
    If compress is set to True all of trailing spaces will be removed out of
    the template (you can call it "minifying" html)
    """

    templ = []
    with open(".templates/%s.html" % template_name) as fobj:
        for line in fobj:
            if line.strip().startswith("<!-- "):
                continue
            if compress:
                templ.append(line.compress())
            else:
                templ.append(line)

    if compress:
        return " ".join(templ)
    else:
        return "".join(templ)


class Article:
    """Represents article"""
    def __init__(self, title, body=None, created=None, updated=None):
        """Create the obj"""
        self.body = body
        self.created = created
        self.title = title
        self.updated = updated

        self.fname = None
        self.html_fname = None
        self.tags = []

    def human_created(self):
        """Return human created date"""
        return self.created.strftime("%d %b, %Y")

    def human_created_detail(self):
        """Return human created date"""
        return self.created.strftime("%A, %d %b, %Y, %X")

    def rfc_created(self):
        """Return RFC 3339 formatted date"""
        return get_rfc3339(self.created)

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
        # if os.stat(".db.sqlite").st_size == 0:
            # self._create_schema()
        self._sorted_articles = []

    def build(self):
        """Convert articles against the template to build directory"""
        if not os.path.exists("build"):
            os.mkdir("build")
            os.mkdir("build/images")
            shutil.copytree(".css", "build/css")
        self._walk()
        self._calculate_tag_cloud()
        self._save()
        shutil.rmtree(os.path.join("build", "images"))
        shutil.copytree(os.path.join("articles", "images"),
                        os.path.join("build", "images"))
        self._tag_pages()
        self._index()
        self._archive()

    def _tag_pages(self):
        """Create pages for the tag links"""
        main = _get_template("main")
        archive_header = _get_template("archive_header")
        headline = _get_template("headline")
        article_tags = _get_template("article_tags")

        tags = defaultdict(list)
        for art in self.articles:
            for tag in art.tags:
                tags[tag].append(art)

        for tag in tags:
            titles = []
            for art in tags[tag]:
                art_tags = ", ".join([article_tags % {"tag_url": trans(tag_),
                                                      "tag": tag_}
                                      for tag_ in art.tags])
                titles.append(headline % {"article_url": art.html_fname,
                                          "title": art.title,
                                          "datetime": art.rfc_created(),
                                          "human_date": art.human_created(),
                                          "tags": art_tags})

            with open(os.path.join("build", "tag-%s.html" % trans(tag)),
                      "w") as fobj:
                header = archive_header % {"title": "Category: %s" % tag}

                fobj.write(main % {"page_header": "import that",
                                   "title": "Category: %s" % tag,
                                   "header": header,
                                   "body": " ".join(titles),
                                   "footer": "",
                                   "class_index": "current",
                                   "class_arch": "",
                                   "tags": self.tag_cloud})

    def _index(self):
        """Create index.html for the main site entry"""
        main = _get_template("main")
        short_article = _get_template("short_article")
        article_tags = _get_template("article_tags")

        titles = []
        for art in self.articles[:5]:
            art_tags = ", ".join([article_tags %
                                  {"tag_url": trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])
            titles.append(short_article % {"article_url": art.html_fname,
                                           "title": art.title,
                                           "datetime": art.rfc_created(),
                                           "human_date": art.human_created(),
                                           "short_body":
                                           art.body.split("<!-- more -->")[0],
                                           "tags": art_tags})

        with open(os.path.join("build", "index.html"), "w") as fobj:

            fobj.write(main % {"page_header": "import that",
                               "title": "",
                               "header": "",
                               "body": " ".join(titles),
                               "footer": "",
                               "class_index": "current",
                               "class_arch": "",
                               "tags": self.tag_cloud})

    def _archive(self):
        """Create atchive.html for the site"""
        main = _get_template("main")
        archive_header = _get_template("archive_header")
        headline = _get_template("headline")
        article_tags = _get_template("article_tags")

        titles = []
        for art in self.articles:
            art_tags = ", ".join([article_tags %
                                  {"tag_url": trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])
            titles.append(headline % {"article_url": art.html_fname,
                                      "title": art.title,
                                      "datetime": art.rfc_created(),
                                      "human_date": art.human_created(),
                                      "tags": art_tags})

        with open(os.path.join("build", "archives.html"), "w") as fobj:
            header = archive_header % {"title": "Archiwum"}

            fobj.write(main % {"page_header": "import that",
                               "title": "Archiwum - ",
                               "header": header,
                               "body": " ".join(titles),
                               "footer": "",
                               "class_index": "",
                               "class_arch": "current",
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
        article_tags = _get_template("article_tags")

        for art in self.articles:

            art_tags = ", ".join([article_tags %
                                  {"tag_url": trans(tag_), "tag": tag_}
                                  for tag_ in art.tags])

            header = article_header % {"title": art.title,
                                       "datetime": art.rfc_created(),
                                       "human_date": art.human_created()}
            footer = article_footer % {'rfc_date': art.rfc_created(),
                                       "datetime": art.human_created_detail(),
                                       "human_date": art.human_created_detail(),
                                       "tags": art_tags}

            match = FILENAME.match(art.fname)
            if match:
                art.html_fname = match.groups()[0].replace("_", "-") + ".html"
            else:
                art.html_fname = art.fname[:-4] + ".html"

            with open(os.path.join("build", art.html_fname), "w") as fobj:
                fobj.write(main % {"page_header": "import that",
                                   "title": art.title + " - ",
                                   "header": header,
                                   "body": art.body,
                                   "footer": footer,
                                   "class_index": "current",
                                   "class_arch": "",
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
            self._harvest(fname)

        self.articles = sorted(self.articles, key=attrgetter('created'),
                               reverse=True)

    def _harvest(self, fname):
        """Gather all the necesary info for the article"""
        print("Processing `%s'" % fname)
        with open(os.path.join("articles", fname)) as fobj:
            html, attrs = blogArticleString(fobj.read())

        art = Article(attrs['title'], html, attrs.get('datetime'),
                      attrs.get('modified'))
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
                                       "tag_url": trans(key),
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
    # Apply curent locale
    locale.setlocale(locale.LC_ALL, locale.getlocale()[0])
    # or, force desired locale:
    #locale.setlocale(locale.LC_ALL, "de_DE")
    sys.exit(ARGS.func(ARGS))
