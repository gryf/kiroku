#!/usr/bin/env python3
"""
Tests for search engine indexer
"""
import unittest

from kiroku import search


class TestMLStripper(unittest.TestCase):
    """Check MLStripper"""

    def setUp(self):
        """Setup"""

        self.html = """<h2>articletitle</h2>
<p>This is an article about <b>Articletitle</b></p>
<p>How about <i>some</i> <i><b>nested</b></i> content?</p>
<p>And what about 喜六 i18n stuff? zażółć gęślą jaźń</p>
<pre
<div class="highlight"><pre><span class="gp"> code </span> <span
class="nv">SOME_MORE_CODE</span>
</pre></div>
<p>Or, the <code>inline_code</code><p>"""

    def test_get_data(self):
        """Tests get_data() method of MLStripper"""
        ml_stripper = search.MLStripper(strict=False)
        ml_stripper.feed(self.html)
        out = ml_stripper.get_data()

        result = {'and': 1,
                  'code': 1,
                  'zażółć': 1,
                  'is': 1,
                  'some': 2,
                  'inline_code': 1,
                  'an': 1,
                  'i18n': 1,
                  'gęślą': 1,
                  'articletitle': 6,
                  'article': 1,
                  'nested': 2,
                  'what': 1,
                  'this': 1,
                  'or': 1,
                  'content': 1,
                  'how': 1,
                  'stuff': 1,
                  'jaźń': 1,
                  'about': 3,
                  'the': 1,
                  '喜六': 1,
                  'some_more_code': 1}

        self.assertEqual(out, result)

if __name__ == '__main__':
        unittest.main()
