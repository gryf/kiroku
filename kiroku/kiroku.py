"""
Kiroku - Manage and create static website.

See README for details
"""
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections import defaultdict
from configparser import SafeConfigParser
import gettext
from math import log
from operator import attrgetter
import json
import locale
import os
import re
import shutil
import sys

from kiroku.article import Article
from kiroku.misc import TR_TABLE
from kiroku.rest import BlogArticle
from kiroku.rss import Rss
from kiroku.template import Template


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
          'locale': ""}


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

    def _join_tags(self, tags):
        """Parse tags and return them as string of tags separated with comma"""
        article_tag = self._templ("article_tag")
        data = [article_tag % {'tag_url': tag_.translate(TR_TABLE),
                               'tag': tag_,
                               'server_root': self._cfg['server_root']}
                for tag_ in tags]
        return ', '.join(data)

    def _create_json_data(self):
        """Create data utilized on the client side - that includes search
        data, articles metadata (titles, links, tags dates and so on),
        template for the search output, etc"""
        print("Writing json data files…")
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
            art_tags = self._join_tags(art.tags)
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
        headline = self._templ("headline")

        tags = defaultdict(list)
        for art in self.articles:
            for tag in art.tags:
                tags[tag].append(art)

        for tag in tags:
            titles = []
            for art in tags[tag]:
                art_tags = self._join_tags(art.tags)
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

            with open(os.path.join("build", "tag-%s.html" %
                                   tag.translate(TR_TABLE)), "w") as fobj:
                fobj.write(main % data)

    def _index(self):
        """Create index.html for the main site entry"""
        print("Creating `index.html'…")
        main = self._templ("main")
        article_short = self._templ("article_short")

        titles = []
        for art in self.articles[:5]:
            short_body = art.body.split("<!-- more -->")[0]
            art_tags = self._join_tags(art.tags)
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
        headline = self._templ("headline")

        titles = []
        for art in self.articles[5:]:
            art_tags = self._join_tags(art.tags)
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
        for art in self.articles:
            art_tags = self._join_tags(art.tags)
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
                    "tag_url": key.translate(TR_TABLE),
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
        shutil.copytree(os.path.join(DATA_DIR, "js"), ".js/")

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
    if arguments == Namespace():  # empty namespace is not what's expected
        parser.print_help()
        sys.exit(2)

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

    if config['locale']:
        locale.setlocale(locale.LC_ALL, config['locale'])
        language = config['locale']
    else:
        locale.setlocale(locale.LC_ALL, "")
        language = ".".join(locale.getdefaultlocale())

    gettext.install(True, localedir=None)
    gettext.find(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    gettext.bind_textdomain_codeset(APP_NAME, "UTF-8")
    lang = gettext.translation(APP_NAME, LOCALE_DIR,
                               languages=[language],
                               fallback=True)
    config.update(get_i18n_strings(lang.gettext))
    return config


def run():
    """Parse command line and execute appropriate action"""
    arguments = parse_commandline()
    sys.exit(arguments.func(arguments, get_config()))
