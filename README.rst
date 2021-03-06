Kiroku
======

.. image:: https://travis-ci.org/gryf/kiroku.svg?branch=master
    :target: https://travis-ci.org/gryf/kiroku

.. image:: https://badge.fury.io/py/kiroku.png
   :target: http://badge.fury.io/py/kiroku

What is Kiroku?
---------------

Kiroku is a tool written in Python for creating and build a fully static blog or
web page. That means, no server side language, framework,
*mod_python*/*mod_wsgi* is needed. To serve such generated content pure web
server is more than enough.

Some highlights:

* Almost no external dependencies (only `docutils`_ is required)
* Works with Python 3
* Modifiable templates
* Simple search
* Generated RSS channel
* i18n aware
* Configurable via ``ini`` file

Kiroku (喜六, in the meaning of putting something into the record; writing
something) name was chosen for this project before I realized, that there
already are software projects with the same name. Most of them are inactive, so
I decided to keep that name.

Requirements
------------

Besides (obviously) Python 3, there is only one dependency - `docutils`_.

For proper date time representation, `pytz`_ module is highly recommended,
unless you are lucky to live in the ``Europe/Warsaw`` or ``UTC`` time zones, or
you simply don't care, and stick with local time represented in UTC format.

Last possible dependency is `pygments`_, which *automagically* enables syntax
highlight in code blocks.

Installation
------------

#. Install globally

   .. code:: shell-session

      root@localhost # pip install kiroku

#. Virtualenv is one option

   .. code:: shell-session

      user@localhost $ virtualenv-python3.2 blog
      New python executable in py3/bin/python3.2
      Also creating executable in py3/bin/python
      Installing distribute...done.
      Installing pip...done.
      user@localhost $ cd blog
      user@localhost blog $ . bin/activate
      (blog)user@localhost blog $ pip install kiroku

#. Also, it can be download and used directly:

   .. code:: shell-session

      user@localhost $ git clone https://bitbucket.org/gryf/kiroku.git
      user@localhost $ cd kiroku
      user@localhost kiroku $ PYTHONPATH=/home/user/kiroku python3 scripts/kiroku --help

   Note, that ``PYTHONPATH`` should be defined correctly.

Usage
-----

Once installed, ``kiroku`` command should be available, and can be used for
building the structure of the blog or web side:

   .. code:: shell-session

      user@localhost $ kiroku init blog

This command will create default directory structure, under which several items
will be available:

- ``articles`` - directory where all articles/posts shall be stored
- ``.css`` - contents of this directory will be copied into destination
  ``build`` - directory as ``css``. All modification to the CSS should be done
  there. File ``/.css/style.css`` is the default (and only) CSS file. Note, that
  during build every file with extension ``.css`` will be minified.
- ``.js`` - directory with JavaScript files. Will be copied to ``build/js``
  during build.
- ``.templates`` - this directory contains all the templates that Kiroku uses
  to build the pages.

Now, just change the directory to ``blog`` and issue the command ``build`` to
generate entire site:

   .. code:: shell-session

      user@localhost $ cd blog
      user@localhost blog $ kiroku build

Generated HTML files, style, JavaScript files - all of that will be placed in
the ``build`` directory.

You can also point the directory, where the blog files lies without changing
the path:

   .. code:: shell-session

      user@localhost $ kiroku build blog

Articles/pages
--------------

Every article, which should be taken into considerations should be placed in
``articles`` directory. Images should be placed in a subdirectory (``images``,
``img``, ``graphics``, ``res`` are the common choices). Files can be named in
any convention, but in two conditions: they must have ``.rst`` extension, and
they have to be on the root of the ``articles`` directory. Kiroku will not scan
that directory recursively. Articles can have date prefix, just to have them
chronologically sorted, for example ``2001-12-17_foo.rst``.

There is one special article file which is treated differently - ``about.rst``.
It doesn't have any fields mentioned below; they will not be processed. As the
name suggest, this is *About me* page.

Each page is a simple reST document. There are two modifications, that are
implemented in the kiroku module, which *make difference* from ordinary reST
document:

#. ``More`` comment.

   If the author place the comment ``.. more`` in the article, it will inform
   the Kiroku, where to cut the page and place the first part (a summary of the
   article, perhaps) of it on the index page, archive, description fields on RSS
   and so on. Example:

   .. code:: rest

      Hendrerit sem, eu tempor nisi felis et metus. Etiam gravida sem ut mi.

      .. more

      Vivamus lacus libero, aliquam eget, iaculis quis, tristique adipiscing,
      diam.  Vivamus nec massa non justo iaculis pellentesque. Aenean accumsan
      elit sit amet nibh feugiat semper.

   That will make only first line to appear on the front page.

   Placing it on the page is not mandatory, so there is no point to
   do it on short articles, but it is a good idea to put it on the huge
   articles, since several huge articles on the front page can annoy readers.

   This idea was taken from blogger platform, but I think, that I saw that on
   other blog platforms too.

#. Special fields

   `Fields`_ are special elements, which may (or may not) be present on the
   document itself, but their role is rather to describe reST document, then
   make significant appearance on that document itself.

   Kiroku use three fields, which will be utilized to describe an article:

   - ``:Title:`` - Field should contain the title of the article. If leaved
     empty, it will be guessed from the file name.
   - ``:Datetime:`` - Creation date. If not provided it will inherit the value
     from article file creation time. Format, as described on `datetime module`_
     is as follows:

        .. code:: python

           "%Y-%m-%d %H:%M:%S"
           # for example:
           "2000-01-24 17:33:31"

   - ``:Tags:`` - Comma separated labels for the article. Of course, can be
     unset.

   All of those fields are optional but it's highly recommended to have them on
   the articles. All fields can be lowrcase or upercase - it does not matter.

Article example:

.. code:: rest

   :Title: My article
   :datetime: 2000-01-24 17:33:31
   :TAGS: Lorem ipsum, blog, cats

   A subsection
   ------------

   Phasellus eu quam. Quisque interdum cursus purus. In orci. Maecenas vehicula.
   Sed et mauris. Praesent feugiat viverra lacus. Suspendisse pulvinar lacus ut
   nunc. Quisque nisi. Suspendisse id risus nec nisi ultrices ornare. Donec eget
   tellus. Nullam molestie placerat felis. Aenean facilisis. Nunc erat.

   .. more

   Another subsection
   ------------------

   Luctus et ultrices posuere cubilia Curae; Morbi urna dui, fermentum quis,
   feugiat imperdiet, imperdiet id, sapien. Phasellus auctor nunc. Vivamus eget
   augue quis neque vestibulum placerat. Duis placerat. Maecenas accumsan rutrum
   lacus. Vestibulum lacinia semper nibh. Aenean diam odio, scelerisque at,
   ullamcorper nec, tincidunt dapibus, quam. Duis vel ante nec tortor porta
   mollis. Praesent orci. Cras dignissim vulputate metus.

If `pygments`_ module is present in the system, syntax highlighting for the code
blocks can be enabled. It is enough to put the appropriate language for such
block, for example::

   .. code:: python

      print("hi")

It will produce:

   .. code:: python

      print("hi")

Configuration
-------------

Kiroku provides simple configuration via ``config.ini`` file. After the
initialization there is an example for the configuration in the file
``config.ini.example``. It can be renamed to the ``config.ini`` and then edited.

Following options under ``[kiroku]`` section are available:

- ``locale`` (default ``en_US.UTF-8``) - language of the web pages.
- ``server_name`` (default ``localhost``) - target server name. It'll be used
  for links in RSS and for `favicon`.
- ``server_root`` (default ``/``) - The root of the page/blog can be set here.
  If set to ``foo``, all the full links will be prefixed with it, i.e.
  ``http://localhost/foo/link.html``.
- ``server_protocol`` (default ``http``) - It may be changed to ``https``
- ``site_name`` (default ``Kiroku``) - Site name. It will be displayed at the
  top of the page.
- ``site_desc`` (default ``Yet another blog``) - description of the
  website/blog. By default only seen on the RSS description tag.
- ``site_footer`` (default ``The footer``) - footer of the page.
- ``timezone`` (default ``UTC``) - proper name of the time zone the dates should
  be represent. Without `pytz`_ module, there is only ``Europe/Warsaw`` and
  ``UTC`` time zones implemented.

Besides configuration, there is possibility to influence the look of the page by
simply adjusting the CSS file and the templates, which can be found under
``.css`` and ``.templates`` directories respectively.

Translations
------------

For now only Polish translation is available. Any help with translation is
welcomed :)

Development
-----------

For development, `virtualenv`_ is strongly recommended. Following dependencies
and tools are required. Python packages:

- `coverage`_ - tool for code coverage measurement
- `slimit`_ - for minifying JavaScript files
- `tox`_ - for test running

Although not necessary, but recommended are two additional packages:

- `pep8`_
- `pylint`_

Which **should** be used during development.

All Python dependencies can be installed inside *virtualenv* environment with
``pip`` command:

.. code:: shell-session

   user@localhost $ virtualenv -p python3 kiroku-ve
   user@localhost $ cd kiroku-ve
   user@localhost kiroku-ve $ . bin/activate
   (kiroku-ve)user@localhost kiroku-ve $ pip install -r dev-requirements.txt

Among the mentioned above packages it will also (try to) install `docutils`_ and
`pygments`_ modules.

If there is a plan for creating new message catalogs, or generating them, there
will be also `GNU gettext`_ needed (tools like ``xgettext`` and  ``msgfmt`` in
particular).

Usually, for simple tasks automation I've been using ``Makefile`` and ``make``
utility, or the `paver`_ python task manager. However I've been trying to
decrease external dependencies only to the really necessary modules, so I've
implemented extra commands to the setup script, so that it can do a bit more
than you'll expect from ``setup.py`` :)

The commands are as follows:

- ``test`` - execute the tests, and display the code coverage for them,
- ``minify`` - minify JavaScript files (for now it is only one),
- ``genpot`` - generate ``.pot`` file out of the source files. File
  ``kiroku.pot`` will be placed under ``kiroku/data/locale`` directory,
- ``gencat`` - generate message catalogs for every available source ``.po``
  files.

Note, that during build, message catalogs will (try to) be regenerated,
otherwise the interface will be in English by default, regardless of the
language in the config.

``test`` command may have two additional parameters:

- ``--verbose`` or ``-v`` - will turn on all of the messages printed out by the
  modules. This could be useful for debugging with ``pdb``.
- ``--coverage`` or ``-c`` - will measure and print out the code coverage

Every command should be executed in the root directory of the Kiroku repository
(the directory where ``setup.py`` exists).

TODO
----

There is still much to do. Here is the list of things I'm planning to do:

#. Module for comments.

   I'm not decided yet on the way to append comments system (if any). For sure
   an obvious choice could be adapting the templates to utilize `disqus`_ or
   similar commenting system, use some self-hosted solution (like `isso`_), or
   even go with moderated (through the email) solutions, as described in `Matt
   Palmer blogpost`_.

#. Make the templates use some engine like `jinja`_ or `mako`_. Initially, I
   have plan to do that, but eventually I've decided to keep Kiroku simple.
   Maybe, if the interest will be big enough, I'll add it later.

License
-------

This software is licensed under Simplified BSD License::

    Copyright (c) 2013, Roman Dobosz
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
   DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
   ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


.. _docutils: http://docutils.sourceforge.net
.. _pygments: http://pygments.org
.. _fields: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#field-lists
.. _datetime module: http://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
.. _virtualenv: http://www.virtualenv.org
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _slimit: https://github.com/rspivak/slimit
.. _GNU gettext: http://www.gnu.org/software/gettext/
.. _paver: http://paver.github.io/paver/
.. _pep8: http://pep8.readthedocs.org/
.. _pylint: http://www.logilab.org/project/pylint
.. _pytz: http://pytz.sourceforge.net
.. _disqus: http://www.disqus.com
.. _isso: http://posativ.org/isso/
.. _Matt Palmer blogpost: http://www.hezmatt.org/~mpalmer/blog/2011/07/19/static-comments-in-jekyll.html
.. _jinja: http://jinja.pocoo.org
.. _mako: http://www.makotemplates.org
.. _tox: https://tox.readthedocs.io
