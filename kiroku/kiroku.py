"""
Kiroku - Manage and create static website.

See README for details
"""
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
import collections
import configparser
import gettext
import json
import locale
import math
import operator
import os
import re
import shutil
import sys

from kiroku import article
from kiroku import misc
from kiroku import rest
from kiroku import rss
from kiroku import template


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
          'locale': "",
          'timezone': "UTC"}


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


def build(opts, cfg):
    """Build the site"""
    kiroku = Kiroku(cfg, opts.path)
    return kiroku.build()


def init(opts, cfg):
    """Initialize given directory with details"""
    kiroku = Kiroku(cfg, opts.path)
    return kiroku.init()


def _minify_css(fname):
    """Minify CSS (destructive!)"""
    comments = re.compile(r'/\*.*?\*/')
    whitespace = re.compile(r'[\n\s\t][\n\s\t]+')
    space = re.compile(r'\s?([;:{},+>])\s?')

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

    def __init__(self, config, path='.'):
        self._about_fname = None
        self._sorted_articles = []
        self._cfg = config
        self.path = path
        self.articles = []
        self.tag_cloud = None
        self.tags = collections.defaultdict(list)
        self._templ = template.Template(config, path)

    def build(self):
        """Convert articles against the template to build directory"""
        if not os.path.exists(os.path.join(self.path, "build")):
            os.makedirs(os.path.join(self.path, "build", "images"))
            shutil.copytree(os.path.join(self.path, ".css"),
                            os.path.join(self.path, "build/css"))
            shutil.copytree(os.path.join(self.path, ".js"),
                            os.path.join(self.path, "build/js"))
            for fname in os.listdir(os.path.join(self.path, "build", "css")):
                if fname.endswith(".css"):
                    _minify_css(os.path.join(self.path, "build", "css", fname))

        self._walk()
        self._calculate_tag_cloud()
        self._create_json_data()
        self._about()
        self._save()

        # copy all the other files and directories content, besides rst files
        _, dirs, files = next(os.walk(os.path.join(self.path, "articles")))
        for dirname in dirs:
            if os.path.exists(os.path.join(self.path, "build", dirname)):
                shutil.rmtree(os.path.join(self.path, "build", dirname))
            shutil.copytree(os.path.join(self.path, "articles", dirname),
                            os.path.join(self.path, "build", dirname))
        for fname in files:
            if fname.lower().endswith("rst"):
                continue

            if os.path.exists(os.path.join(self.path, "build", fname)):
                os.unlink(os.path.join(self.path, "build", fname))
            shutil.copy(os.path.join(self.path, "articles", fname),
                        os.path.join(self.path, "build", fname))

        shutil.copy(os.path.join(self.path, ".templates/favicon.ico"),
                    os.path.join(self.path, "build/images"))
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
        rssobj = rss.Rss(self._cfg, self.path)

        for art in self.articles[:10]:
            data = {"article_title": art.title,
                    "article_link": art.html_fname,
                    "pub_date": art.created_rfc822(),
                    "item_desc": art.get_short_body()}
            rssobj.add(data)

        with open(os.path.join(self.path, "build", "rss.xml"), "w") as fobj:
            fobj.write(rssobj.get())

    def _join_tags(self, tags):
        """Parse tags and return them as string of tags separated with comma"""
        data = [self._templ("article_tag",
                            {'tag_url': tag_.translate(misc.TR_TABLE),
                             'tag': tag_})
                for tag_ in tags]
        return ', '.join(data)

    def _create_json_data(self):
        """Create data utilized on the client side - that includes search
        data, articles metadata (titles, links, tags dates and so on),
        template for the search output, etc"""
        print("Writing json data files…")
        with open(os.path.join(self.path, "build", "templates.json"),
                  "w") as fobj:
            json.dump({"w": "<h1>%(i18n_search_progress)s</h1>" % self._cfg,
                       "r": "<h1>%(i18n_search_results)s</h1>" % self._cfg,
                       "t":  self._cfg["i18n_search_results_ttile"] +
                       " - " + self._cfg["site_name"],
                       "n": "<h1>%(i18n_search_not_found)s</h1>" % self._cfg},
                      fobj, ensure_ascii=False)

        words = {"a": [],  # article data
                 "w": {}}  # word list
        _ids = []
        for art in self.articles:
            art_tags = self._join_tags(art.tags)

            words['a'].append(self._templ("headline",
                                          {"article_url": art.html_fname,
                                           "title": art.title,
                                           "datetime": art.created_rfc3339(),
                                           "human_date": art.created_short(),
                                           "tags": art_tags}))

            _ids.append(art.html_fname)
            idx = _ids.index(art.html_fname)

            art_words = art.get_words()
            for word in art_words:
                if word not in words["w"]:
                    words["w"][word] = [(idx, art_words[word])]
                else:
                    words["w"][word].append((idx, art_words[word]))

        with open(os.path.join(self.path, "build", "search.json"),
                  "w") as fobj:
            json.dump(words, fobj, ensure_ascii=False)

    def _tag_pages(self):
        """Create pages for the tag links"""
        print("Creating tag pages…")

        tags = collections.defaultdict(list)
        for art in self.articles:
            for tag in art.tags:
                tags[tag].append(art)

        for tag in tags:
            titles = []
            for art in tags[tag]:
                art_tags = self._join_tags(art.tags)
                titles.append(self._templ("headline",
                                          {"article_url": art.html_fname,
                                           "title": art.title,
                                           "datetime": art.created_rfc3339(),
                                           "human_date": art.created_short(),
                                           "tags": art_tags}))

            title = self._cfg['i18n_art_tags'] % tag

            with open(os.path.join(self.path, "build", "tag-%s.html" %
                                   tag.translate(misc.TR_TABLE)), "w") as fobj:

                data = {"title": title + " - ",
                        "header": self._templ("header", {"title": title}),
                        "body": " ".join(titles),
                        "class_index": "current",
                        "class_arch": "",
                        "class_about": "",
                        "footer": "",
                        "tag_cloud": self.tag_cloud}

                fobj.write(self._templ("main", data))

    def _index(self):
        """Create index.html for the main site entry"""
        print("Creating `index.html'…")

        titles = []
        for art in self.articles[:5]:
            short_body = art.body.split("<!-- more -->")[0]
            art_tags = self._join_tags(art.tags)

            titles.append(self._templ("article_short",
                                      {"article_url": art.html_fname,
                                       "title": art.title,
                                       "datetime": art.created_rfc3339(),
                                       "human_date": art.created_short(),
                                       "short_body": short_body,
                                       "tags": art_tags}))

        with open(os.path.join(self.path, "build", "index.html"), "w") as fobj:
            fobj.write(self._templ("main",
                                   {"title": "",
                                    "header": "",
                                    "body": " ".join(titles),
                                    "class_index": "current",
                                    "class_arch": "",
                                    "class_about": "",
                                    "footer": "",
                                    "tag_cloud": self.tag_cloud}))

    def _archive(self):
        """Create archive.html for the site"""
        print("Create archive page…")

        titles = []
        for art in self.articles[5:]:
            art_tags = self._join_tags(art.tags)
            titles.append(self._templ("headline",
                                      {"article_url": art.html_fname,
                                       "title": art.title,
                                       "datetime": art.created_rfc3339(),
                                       "human_date": art.created_short(),
                                       "tags": art_tags}))

        title = self._cfg['i18n_archives']

        with open(os.path.join(self.path, "build", "archives.html"),
                  "w") as fobj:
            fobj.write(self._templ("main",
                                   {"title": title + " - ",
                                    "header": self._templ("header",
                                                          {"title": title}),
                                    "body": " ".join(titles),
                                    "class_index": "",
                                    "class_arch": "current",
                                    "class_about": "",
                                    "footer": "",
                                    "tag_cloud": self.tag_cloud}))

    def _save(self):
        """
        Save articles and other generated pages into html using the templates.
        """
        print("Saving articles…")
        for art in self.articles:
            art_tags = self._join_tags(art.tags)
            header = self._templ("article_header",
                                 {"title": art.title,
                                  "datetime": art.created_rfc3339(),
                                  "human_date": art.created_short()})
            footer = self._templ("article_footer",
                                 {'rfc_date': art.created_rfc3339(),
                                  "datetime": art.created_detailed(),
                                  "human_date": art.created_detailed(),
                                  "tags": art_tags})

            with open(os.path.join(self.path, "build", art.html_fname),
                      "w") as fobj:
                fobj.write(self._templ("main",
                                       {"title": art.title + " - ",
                                        "header": header,
                                        "body": art.body,
                                        "class_index": "current",
                                        "class_arch": "",
                                        "class_about": "",
                                        "footer": footer,
                                        "tag_cloud": self.tag_cloud}))

    def _walk(self):
        """Walk through the flat list of the articles and gather all of the
        goodies"""
        print("Gathering articles…")
        art_filenames = os.listdir(os.path.join(self.path, "articles"))

        for fname in art_filenames:
            full_path = os.path.join(self.path, "articles", fname)
            if not fname.endswith(".rst"):
                continue
            if fname == "about.rst":
                self._about_fname = full_path
            else:
                self._harvest(full_path)

        self.articles = sorted(self.articles,
                               key=operator.attrgetter('created'),
                               reverse=True)
        print("…done. Articles found: %d" % len(self.articles))

    def _about(self):
        """Save special page "about" """
        if not self._about_fname:
            print("No about page found")
            return

        print("Generating about page…")

        with open(self._about_fname) as fobj:
            html, dummy = rest.BlogArticle(fobj.read()).publish()

        title = self._cfg["i18n_about"]

        with open(os.path.join(self.path, "build", "about.html"), "w") as fobj:
            fobj.write(self._templ("main",
                                   {"title": title + " - ",
                                    "header": self._templ("header",
                                                          {"title": title}),
                                    "body": html,
                                    "class_index": "",
                                    "class_arch": "",
                                    "class_about": "current",
                                    "footer": "",
                                    "tag_cloud": self.tag_cloud}))

    def _harvest(self, fname):
        """Gather all the necessary info for the article"""
        print("Processing `%s'" % fname)
        art = article.Article(fname, self._cfg)
        art.read()
        self.articles.append(art)

        for tag in art.tags:
            self.tags[tag].append(fname)

    def _calculate_tag_cloud(self):
        """Calculate tag cloud."""
        print("Calculating tag cloud…")
        if self.tag_cloud:
            return self.tag_cloud

        self.tag_cloud = {}

        tag_weight = {}
        biggest = 0

        for tag in self.tags:
            tag_weight[tag] = len(self.tags[tag])
            biggest = tag_weight[tag] if tag_weight[tag] > biggest else biggest

        low = 1
        high = 9

        for tag in self.tags:
            if math.log(biggest):
                size = (math.log(tag_weight[tag]) /
                        math.log(biggest)) * (high - low) + low
            else:
                size = 9
            self.tag_cloud[tag] = size

        tag_cloud = []
        for key in sorted(self.tags):
            tag_url = key.translate(misc.TR_TABLE)
            tag_cloud.append(self._templ("tag",
                                         {"size": self.tag_cloud[key],
                                          "tag": key,
                                          "tag_url": tag_url,
                                          "count": tag_weight[key]}))

        self.tag_cloud = " ".join(tag_cloud)

    def init(self):
        """Initialize given directory with details"""
        if os.path.exists(self.path):
            print("File or directory `%s' exists. Remove it, or choose "
                  "another directory." % self.path)
            return 1

        print("Initializing `%s'" % self.path)

        os.mkdir(self.path)

        shutil.copytree(os.path.join(DATA_DIR, "articles"),
                        os.path.join(self.path, "articles"))
        shutil.copytree(os.path.join(DATA_DIR, "css"),
                        os.path.join(self.path, ".css"))
        shutil.copytree(os.path.join(DATA_DIR, "js"),
                        os.path.join(self.path, ".js/"))

        shutil.copytree(os.path.join(DATA_DIR, "templates"),
                        os.path.join(self.path, ".templates"))
        shutil.copy(os.path.join(DATA_DIR, "config.ini.example"), self.path)
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
    build_cmd.add_argument("path", default=".", nargs='?')
    build_cmd.set_defaults(func=build)

    arguments = parser.parse_args(args)
    if arguments == Namespace():  # empty namespace is not what's expected
        parser.print_help()
        sys.exit(2)

    return arguments


def get_config(args):
    """Read and return configuration dictionary."""
    config = CONFIG
    conf = configparser.SafeConfigParser(defaults=CONFIG)
    path = args.path if args.path else '.'
    conf.read(os.path.join(path, "config.ini"))

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
    sys.exit(arguments.func(arguments, get_config(arguments)))
