"""
Setup for the Kiroku project
"""
from distutils.command import sdist, build
from distutils.core import setup, Command
from unittest import TestLoader, TextTestRunner
import os
import sys
import re
import shutil
from tempfile import mkdtemp


try:
    import coverage
except ImportError:
    coverage = None

try:
    import slimit
except ImportError:
    slimit = None


def find_dists():
    """Grab all of the files, compare it against blacklist and return as
    list"""
    retlist = []
    blacklist = ['kiroku.pot', 'kiroku_pl.po', 'search.js']
    for root, dummy, files in os.walk("kiroku/data"):
        for fname in files:
            if fname not in blacklist:
                retlist.append(os.path.join(root, fname)[7:])

    return retlist


class MinifyJavaScript(Command):
    """Minify javascript files under kiroku/data/js directory"""
    user_options = []
    description = __doc__

    def initialize_options(self):
        """Has to beimplemented; not needed though"""

    def finalize_options(self):
        """Has to beimplemented; not needed though"""

    def run(self):
        """Execute command"""
        if not slimit:
            print("You need `slimit' module to minify JavaScript files")
            return

        for root, dirs, files in os.walk("kiroku/data/js"):
            for fname in files:
                if ".min." in fname:
                    continue

                fname = os.path.join(root, fname)
                minified = None
                new_name, ext = os.path.splitext(fname)
                new_name = os.path.join(new_name + ".min" + ext)

                with open(fname) as fobj:
                    minified = slimit.minify(fobj.read(), mangle=True)

                if minified:
                    with open(new_name, "w") as fobj:
                        fobj.write(minified)


class GeneratePot(Command):
    """Generate `pot' template using xgettext"""
    user_options = []
    description = __doc__

    def initialize_options(self):
        """Has to beimplemented; not needed though"""

    def finalize_options(self):
        """Has to beimplemented; not needed though"""

    def run(self):
        """Execute command"""
        os.system('xgettext -o kiroku/data/locale/kiroku.pot kiroku/*.py')


class GenerateMo(Command):
    """Generate message catalogs out of `po' files"""
    user_options = []
    description = __doc__

    def initialize_options(self):
        """Has to beimplemented; not needed though"""
        self.filename_pattern = re.compile("^kiroku_(..).po$")

    def finalize_options(self):
        """Has to beimplemented; not needed though"""

    def run(self):
        """Generate mo files"""
        files = {}
        for fname in os.listdir("kiroku/data/locale"):
            match = self.filename_pattern.match(fname)
            if match:
                files[match.groups()[0]] = os.path.join("kiroku", "data",
                                                        "locale", fname)

        for lang in files:
            path = os.path.join("kiroku/data/locale", lang, "LC_MESSAGES")
            if not os.path.exists(path):
                os.makedirs(path)

            mo_file = os.path.join(path, 'kiroku.mo')
            os.system("msgfmt -o %(path)s %(fname)s" %
                      {'path': mo_file, 'fname': files[lang]})
            # append generated file path without leading 'kiroku/'
            self.distribution.package_data['kiroku'].append(mo_file[7:])


class TestRunner(Command):
    """Run the test suite with optional coverage report"""
    user_options = []
    description = __doc__

    def initialize_options(self):
        """Has to beimplemented; not needed though"""

    def finalize_options(self):
        """Has to beimplemented; not needed though"""

    def run(self):
        """Execute tests. Basically this is a hack to make tests run ALSO on
        virtualenv environment. Also - because tests will run just fine with
        docutils system wide installed, and kiroku as a git cloned repository.

        Docutils have resource location implemented with heavy usage of
        __file__ location with os.path, os.getcwd and so on, Moreover if paths
        are equal on first two position in the path (for example:
            foo/bar/baz
            foo/bar/fizz
        OR
            /foo/bar/baz
            /foo/fizz/bizz
        see docutils.utils.__init__.py:relative_path function) it will
        calculate such directories AS RELATIVE paths, which completely break
        thing if we change the path with os.chdir, after importing or
        registering docutils objects (which have a place in kiroku.py module)
        - obviously it's done before any test case fires.

        This probably will break anyway in case you create virtualenv in the
        same directory as mkdtemp will do (/tmp by default).
        """
        _curdir = os.getcwd()
        _dir = mkdtemp()
        os.chdir(_dir)
        sys.path.insert(0, '.')

        try:
            shutil.copytree(os.path.join(_curdir, "kiroku"), "kiroku")
            if coverage:
                cov = coverage.coverage()
                cov.start()
            loader = TestLoader()
            suite = loader.discover(os.path.join(_curdir, "tests"),
                                    pattern="test_*")
            TextTestRunner().run(suite)
            if coverage:
                cov.stop()
                cov.report(include=["*/kiroku/*.py"], omit=["*test_*"])
        finally:
            os.chdir(_curdir)
            shutil.rmtree(_dir)


class CustomBuild(build.build):
    """Additional steps for build process"""

    def run(self):
        """Modify build process"""
        GenerateMo(self.distribution).run()
        super().run()
        shutil.copyfile("README", os.path.join(self.build_lib,
                                               self.distribution.packages[0],
                                               'data/articles/readme.rst'))


class CustomSdist(sdist.sdist):
    """Additional steps for sdist process"""

    def run(self):
        GenerateMo(self.distribution).run()
        super().run()


setup(name="kiroku",
      packages=["kiroku"],
      package_data={"kiroku": find_dists()},
      version="0.8.0",
      description="Static blog generator",
      author="Roman Dobosz",
      author_email="gryf73@gmail.com",
      url="https://bitbucket.org/gryf/kiroku",
      download_url="https://bitbucket.org/gryf/kiroku.git",
      keywords=["web", "static", "generator", "blog"],
      requires=["docutils"],
      scripts=["scripts/kiroku"],
      classifiers=["Programming Language :: Python :: 3",
                   "Development Status :: 4 - Beta",
                   "Environment :: Console",
                   "Intended Audience :: End Users/Desktop",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Text Processing :: Linguistic",
                   "Topic :: Text Processing :: Markup",
                   "Topic :: Text Processing :: Markup :: HTML"],
      long_description=open("README").read(),
      cmdclass={'build': CustomBuild,
                'gencat': GenerateMo,
                'genpot': GeneratePot,
                'minify': MinifyJavaScript,
                'sdist': CustomSdist,
                'test': TestRunner})
