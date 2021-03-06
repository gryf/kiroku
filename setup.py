#!/usr/bin/env python3
"""
Setup for the Kiroku project
"""
from distutils.command import build
from distutils.command import sdist
import os
import re
import shlex
import shutil
import subprocess
import sys

from setuptools import setup
from setuptools import Command
from setuptools.command.test import test as TestCommand


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

        for root, _, files in os.walk("kiroku/data/js"):
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
                    # append minified file path without leading 'kiroku/'
                    new_name = new_name[7:]
                    self.distribution.package_data['kiroku'].append(new_name)


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
        subprocess.call(['xgettext', '--from-code=utf-8', '-o',
                         'kiroku/data/locale/kiroku.pot'] +
                        [os.path.join('kiroku', x)
                         for x in os.listdir('kiroku') if x.endswith('.py')])


class GenerateMo(Command):
    """Generate message catalogs out of `po' files"""
    user_options = []
    description = __doc__

    def initialize_options(self):
        """Initialization. filename_pattern will filter out all filenames but
        `kiroku_XX.po' where XX is an two letter country/language symbol"""
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


class CustomBuild(build.build):
    """Additional steps for build process"""

    def run(self):
        """Modify build process"""
        GenerateMo(self.distribution).run()
        MinifyJavaScript(self.distribution).run()
        super().run()
        shutil.copyfile("README.rst",
                        os.path.join(self.build_lib,
                                     self.distribution.packages[0],
                                     'data/articles/readme.rst'))


class CustomSdist(sdist.sdist):
    """Additional steps for sdist process"""

    def run(self):
        GenerateMo(self.distribution).run()
        MinifyJavaScript(self.distribution).run()
        super().run()


class Test(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setup(name="kiroku",
      packages=["kiroku"],
      package_data={"kiroku": find_dists()},
      version="0.9.0",
      description="Static blog generator",
      author="Roman Dobosz",
      author_email="gryf73@gmail.com",
      url="https://bitbucket.org/gryf/kiroku",
      download_url="https://bitbucket.org/gryf/kiroku.git",
      keywords=["web", "static", "generator", "blog"],
      install_requires=["docutils==0.13.1"],
      scripts=["scripts/kiroku"],
      classifiers=["Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Development Status :: 4 - Beta",
                   "Environment :: Console",
                   "Intended Audience :: End Users/Desktop",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Text Processing :: Linguistic",
                   "Topic :: Text Processing :: Markup",
                   "Topic :: Text Processing :: Markup :: HTML"],
      long_description=open("README.rst").read(),
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      cmdclass={'build': CustomBuild,
                'gencat': GenerateMo,
                'genpot': GeneratePot,
                'minify': MinifyJavaScript,
                'sdist': CustomSdist,
                'test': Test})
