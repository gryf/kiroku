#!/usr/bin/env python3
# encoding: utf-8
"""
Kiroku - Manage and create static website.

See README for details
"""
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import defaultdict
from configparser import SafeConfigParser
from datetime import datetime
import gettext
from math import log
from operator import attrgetter
import json
import locale
import os
import re
import shutil
import sys

from kiroku.rest import BlogArticle
from kiroku.naive_tzinfo import get_rfc3339, get_rfc822
from kiroku.search import MLStripper


APP_NAME = "kiroku"
MODULE_DIR = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_DIR, "data")
LOCALE_DIR = os.path.join(DATA_DIR, 'locale')

CONFIG = {'server_name': "localhost",
          'server_root': "/",
          'server_protocol': "http",
          'site_name': "Kiroku",
          'site_desc': "Yet another blog",
          'site_footer': "The footer",
          'locale': "C"}

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


def get_i18n_strings(_):
    """Return translations for i18n strings"""
    return {"i18n_art_tags": _("Articles with tag: %s"),
            "i18n_tags": _("Tags"),
            "i18n_about": _("About me"),
            "i18n_archives": _("Archives"),
            "i18n_main": _("Blog"),
            "i18n_rss_feed": _("RSS feed"),
            "i18n_noscript": _("Please, enable JavaScript in order to use "
                               "searching feature."),
            "i18n_search": _("Search"),
            "i18n_search_placeholder": _("Search…"),
            "i18n_search_results_ttile": _("Search results"),
            "i18n_search_progress": _("Search in progress. Please wait."),
            "i18n_search_results": _("Results for phrase \"{sp}\""),
            "i18n_search_not_found": _("No results for phrase \"{sp}\""),
            "i18n_subscribe": _("Subscribe"),
            "i18n_subscribe_desc": _("Subscribe via RSS")}


def build(unused, cfg):
    """Build the site"""
    kiroku = Kiroku(cfg)
    return kiroku.build()


def init(argparse, cfg):
    """Initialize given directory with details"""
    kiroku = Kiroku(cfg)
    return kiroku.init(argparse.path)


def _trans(string):
    """Translate string to remove accented letters"""
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


class Rss:
    """Rss representation class"""
    def __init__(self, cfg):
        """Initialize RSS container"""
        self.items = []
        self._templ = Template()
        self._cfg = cfg

    def add(self, item):
        """Add rss item to the list. Parameter item is a dictionary which
        contains 4 keys with corresponding values:

            title - title of the article
            link - link to the article
            desc - description/first paragraph of the article
            date - publish date in format "Sun, 29 Sep 2002 19:09:28 GMT"
        """
        rss_item = self._templ("rss_item")
        item.update(self._cfg)
        self.items.append(rss_item % item)

    def get(self):
        """Return RSS XML string"""
        rss_main = self._templ("rss_main")

        data = {"items": "\n".join(self.items)}
        data.update(self._cfg)
        return rss_main % data


class Article:
    """Represents article"""

    def __init__(self, fname, cfg):
        """Create the obj"""
        self._fname = fname
        self.body = None
        self.created = None
        self.html_fname = None
        self.tags = []
        self.title = None
        self._cfg = cfg

    def read(self):
        """Read article and transform to html"""
        html, attrs = self._transfrom_to_html()
        self.body = html
        self._process_attrs(attrs)
        self._set_html_name()

    def get_words(self):
        """Return word dictionary out of the html and article attributes"""
        ml_stripper = MLStripper(strict=False)
        ml_stripper.feed(self.body)
        return ml_stripper.get_data()

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
        locale.setlocale(locale.LC_ALL, self._cfg["locale"])
        return date

    def _transfrom_to_html(self):
        """Return processed article and its fields"""
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
            self.title = os.path.splitext(os.path.basename(self._fname))[0]

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

    def __init__(self, cfg):
        self._about_fname = None
        self._sorted_articles = []
        self._cfg = cfg
        self.articles = []
        self.tag_cloud = None
        self.tags = defaultdict(list)
        self._templ = Template()

    def build(self):
        """Convert articles against the template to build directory"""
        if not os.path.exists("build"):
            os.makedirs(os.path.join("build", "images"))
            shutil.copytree(".css", "build/css")
            shutil.copytree(".js", "build/js")
            for fname in os.listdir(os.path.join("build", "css")):
                if fname.endswith(".css"):
                    _minify_css(os.path.join("build", "css", fname))

        self._walk()
        self._calculate_tag_cloud()
        self._create_json_data()
        self._about()
        self._save()

        # copy all the other files and directories content, besides rst files
        _, dirs, files = next(os.walk("articles"))
        for dirname in dirs:
            if os.path.exists(os.path.join("build", dirname)):
                shutil.rmtree(os.path.join("build", dirname))
            shutil.copytree(os.path.join("articles", dirname),
                            os.path.join("build", dirname))
        for fname in files:
            if os.path.exists(os.path.join("build", fname)):
                os.unlink(os.path.join("build", fname))
            shutil.copy(os.path.join("articles", fname),
                        os.path.join("build", fname))

        shutil.copy(".templates/favicon.ico", "build/images")
        self._tag_pages()
        self._index()
        self._archive()
        self._rss()
        print("…all done.")
        return 0

    def _rss(self):
        """Write rss.xml file"""
        if not self.articles:
            return

        print("Writing RSS file…")
        rss = Rss(self._cfg)

        for art in self.articles[:10]:
            data = {"article_title": art.title,
                    "article_link": art.html_fname,
                    "pub_date": art.created_rfc822(),
                    "item_desc": art.get_short_body()}
            rss.add(data)

        with open(os.path.join("build", "rss.xml"), "w") as fobj:
            fobj.write(rss.get())

    def _create_json_data(self):
        """Create data utilized on the client side - that includes search
        data, articles metadata (titles, links, tags dates and so on),
        template for the search output, etc"""
        print("Writing json data files…")
        article_tag = self._templ("article_tag")
        headline = self._templ("headline")
        with open(os.path.join("build", "templates.json"), "w") as fobj:
            json.dump({"w": "<h1>%(i18n_search_progress)s</h1>" % self._cfg,
                       "r": "<h1>%(i18n_search_results)s</h1>" % self._cfg,
                       "t":  self._cfg["i18n_search_results_ttile"] +
                       " - " + self._cfg["site_name"],
                       "n": "<h1>%(i18n_search_results)s</h1>" % self._cfg},
                      fobj, ensure_ascii=False)

        words = {"a": [],  # article data
                 "w": {}}  # word list
        _ids = []
        for art in self.articles:
            data = [article_tag % {"tag_url": _trans(tag_),
                                   "tag": tag_,
                                   'server_root': self._cfg['server_root']}
                    for tag_ in art.tags]
            art_tags = ", ".join(data)
            data = {"article_url": art.html_fname,
                    "title": art.title,
                    "datetime": art.created_rfc3339(),
                    "human_date": art.created_short(),
                    "tags": art_tags}
            data.update(self._cfg)

            words['a'].append(headline % data)

            _ids.append(art.html_fname)
            idx = _ids.index(art.html_fname)

            art_words = art.get_words()
            for word in art_words:
                if word not in words["w"]:
                    words["w"][word] = [(idx, art_words[word])]
                else:
                    words["w"][word].append((idx, art_words[word]))

        with open(os.path.join("build", "search.json"), "w") as fobj:
            json.dump(words, fobj, ensure_ascii=False)

    def _tag_pages(self):
        """Create pages for the tag links"""
        print("Creating tag pages…")
        main = self._templ("main")
        header = self._templ("header")
        article_tag = self._templ("article_tag")
        headline = self._templ("headline")

        tags = defaultdict(list)
        for art in self.articles:
            for tag in art.tags:
                tags[tag].append(art)

        for tag in tags:
            titles = []
            for art in tags[tag]:
                data = [article_tag % {"tag_url": _trans(tag_),
                                       "tag": tag_,
                                       "server_root": self._cfg["server_root"]}
                        for tag_ in art.tags]

                art_tags = ", ".join(data)
                data = {"article_url": art.html_fname,
                        "title": art.title,
                        "datetime": art.created_rfc3339(),
                        "human_date": art.created_short(),
                        "tags": art_tags}
                data.update(self._cfg)
                titles.append(headline % data)

            title = self._cfg['i18n_art_tags'] % tag
            data = {"title": title + " - ",
                    "header": header % {"title": title},
                    "body": " ".join(titles),
                    "class_index": "current",
                    "class_arch": "",
                    "class_about": "",
                    "tag_cloud": self.tag_cloud}
            data.update(self._cfg)
            data["footer"] = ""

            with open(os.path.join("build", "tag-%s.html" % _trans(tag)),
                      "w") as fobj:
                fobj.write(main % data)

    def _index(self):
        """Create index.html for the main site entry"""
        print("Creating `index.html'…")
        main = self._templ("main")
        article_tag = self._templ("article_tag")
        article_short = self._templ("article_short")

        titles = []
        for art in self.articles[:5]:
            short_body = art.body.split("<!-- more -->")[0]
            data = [article_tag % {"tag_url": _trans(tag_),
                                   "tag": tag_,
                                   "server_root": self._cfg["server_root"]}
                    for tag_ in art.tags]
            art_tags = ", ".join(data)
            data = {"article_url": art.html_fname,
                    "title": art.title,
                    "datetime": art.created_rfc3339(),
                    "human_date": art.created_short(),
                    "short_body": short_body,
                    "tags": art_tags}
            data.update(self._cfg)
            titles.append(article_short % data)

        data = {"title": "",
                "header": "",
                "body": " ".join(titles),
                "class_index": "current",
                "class_arch": "",
                "class_about": "",
                "tag_cloud": self.tag_cloud}
        data.update(self._cfg)
        data['footer'] = ""

        with open(os.path.join("build", "index.html"), "w") as fobj:
            fobj.write(main % data)

    def _archive(self):
        """Create atchive.html for the site"""
        print("Create archive page…")
        main = self._templ("main")
        header = self._templ("header")
        article_tag = self._templ("article_tag")
        headline = self._templ("headline")

        titles = []
        for art in self.articles[5:]:
            data = [article_tag % {"tag_url": _trans(tag_),
                                   "tag": tag_,
                                   "server_root": self._cfg["server_root"]}
                    for tag_ in art.tags]
            art_tags = ", ".join(data)
            data = {"article_url": art.html_fname,
                    "title": art.title,
                    "datetime": art.created_rfc3339(),
                    "human_date": art.created_short(),
                    "tags": art_tags}
            data.update(self._cfg)
            titles.append(headline % data)
        title = self._cfg['i18n_archives']
        data = {"title": title + " - ",
                "header": header % {"title": title},
                "body": " ".join(titles),
                "class_index": "",
                "class_arch": "current",
                "class_about": "",
                "tag_cloud": self.tag_cloud}
        data.update(self._cfg)
        data['footer'] = ""

        with open(os.path.join("build", "archives.html"), "w") as fobj:
            fobj.write(main % data)

    def _save(self):
        """
        Save articles and other generated pages into html using the templates.
        """
        print("Saving articles…")
        main = self._templ("main")
        article_header = self._templ("article_header")
        article_footer = self._templ("article_footer")
        article_tag = self._templ("article_tag")
        for art in self.articles:
            data = [article_tag % {"tag_url": _trans(tag_),
                                   "tag": tag_,
                                   "server_root": self._cfg["server_root"]}
                    for tag_ in art.tags]
            art_tags = ", ".join(data)

            header = article_header % {"title": art.title,
                                       "datetime": art.created_rfc3339(),
                                       "human_date": art.created_short()}
            data = {'rfc_date': art.created_rfc3339(),
                    "datetime": art.created_detailed(),
                    "human_date": art.created_detailed(),
                    "tags": art_tags}
            data.update(self._cfg)
            footer = article_footer % data

            data = {"title": art.title + " - ",
                    "header": header,
                    "body": art.body,
                    "class_index": "current",
                    "class_arch": "",
                    "class_about": "",
                    "tag_cloud": self.tag_cloud}
            data.update(self._cfg)
            data["footer"] = footer

            with open(os.path.join("build", art.html_fname), "w") as fobj:
                fobj.write(main % data)

    def _walk(self):
        """Walk through the flat list of the articles and gather all of the
        goodies"""
        print("Gathering articles…")
        art_filenames = os.listdir("articles")

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
        print("…done. Articles found: %d" % len(self.articles))

    def _about(self):
        """Save special page "about" """
        if not self._about_fname:
            print("No about page found")
            return

        print("Generating about page…")

        main = self._templ("main")
        header = self._templ("header")

        with open(self._about_fname) as fobj:
            html, dummy = BlogArticle(fobj.read()).publish()

        title = self._cfg["i18n_about"]
        data = {"title": title + " - ",
                "header": header % {"title": title},
                "body": html,
                "class_index": "",
                "class_arch": "",
                "class_about": "current",
                "tag_cloud": self.tag_cloud}
        data.update(self._cfg)
        data["footer"] = ""

        with open(os.path.join("build", "about.html"), "w") as fobj:
            fobj.write(main % data)

    def _harvest(self, fname):
        """Gather all the necessary info for the article"""
        print("Processing `%s'" % fname)
        art = Article(fname, self._cfg)
        art.read()
        self.articles.append(art)

        for tag in art.tags:
            self.tags[tag].append(fname)

    def _calculate_tag_cloud(self):
        """Calculate tag cloud."""
        print("Calculating tag cloud…")
        if self.tag_cloud:
            return self.tag_cloud

        tag_tmpl = self._templ("tag")

        self.tag_cloud = {}

        tag_wieght = {}
        biggest = 0

        for tag in self.tags:
            tag_wieght[tag] = len(self.tags[tag])
            biggest = tag_wieght[tag] if tag_wieght[tag] > biggest else biggest

        low = 1
        high = 9

        for tag in self.tags:
            if log(biggest):
                size = (log(tag_wieght[tag]) /
                        log(biggest)) * (high - low) + low
            else:
                size = 9
            self.tag_cloud[tag] = size

        tag_cloud = []
        for key in sorted(self.tags):
            data = {"size": self.tag_cloud[key],
                    "tag": key,
                    "tag_url": _trans(key),
                    "count": tag_wieght[key]}
            data.update(self._cfg)
            tag_cloud.append(tag_tmpl % data)

        self.tag_cloud = " ".join(tag_cloud)

    def init(self, target):
        """Initialize given directory with details"""
        if os.path.exists(target):
            print("File or directory `%s' exists. Removing. You may commit "
                     "seppuku." % target)
            shutil.rmtree(target)

        print("Initializing `%s'" % target)

        os.mkdir(target)
        os.chdir(target)

        shutil.copytree(os.path.join(DATA_DIR, "articles"), "articles")
        shutil.copytree(os.path.join(DATA_DIR, "css"), ".css")

        os.mkdir(".js")
        shutil.copy(os.path.join(DATA_DIR, "js", "jquery.min.js"), ".js/")
        shutil.copy(os.path.join(DATA_DIR, "js", "search.min.js"), ".js/")

        shutil.copytree(os.path.join(DATA_DIR, "templates"), ".templates")
        shutil.copy(os.path.join(DATA_DIR, "config.ini.example"), ".")
        print('OK.')
        return 0


def parse_commandline(args=None):
    """Parse commandline options. Return the object"""
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)

    subparser = parser.add_subparsers()
    init_cmd = subparser.add_parser("init", help="Initialize provided "
                                    "directory with the defaults. If "
                                    "directory exists it will be wiped out. "
                                    "You have been warned.")
    init_cmd.add_argument("path")
    init_cmd.set_defaults(func=init)

    build_cmd = subparser.add_parser("build", help="Build entire site, or "
                                     "selected file. If no file path is "
                                     "provided, default `articles' will be "
                                     "processed.")
    build_cmd.set_defaults(func=build)

    arguments = parser.parse_args(args)

    return arguments


def get_config():
    """Read and return configuration dictionary."""
    config = CONFIG
    conf = SafeConfigParser(defaults=CONFIG)
    conf.read("config.ini")

    if 'kiroku' in conf.sections():
        for key in CONFIG:
            config[key] = conf.get('kiroku', key)

    if not config['server_root'].startswith("/"):
        config['server_root'] = "/" + config['server_root']
    if not config['server_root'].endswith("/"):
        config['server_root'] = config['server_root'] + "/"

    locale.setlocale(locale.LC_ALL, config['locale'])
    gettext.install(True, localedir=None)
    gettext.find(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    gettext.bind_textdomain_codeset(APP_NAME, "UTF-8")
    lang = gettext.translation(APP_NAME, LOCALE_DIR,
                               languages=[config['locale']],
                               fallback=True)
    config.update(get_i18n_strings(lang.gettext))
    return config


def run():
    """Parse command line and execute appropriate action"""
    arguments = parse_commandline()
    sys.exit(arguments.func(arguments, get_config()))
