# encoding: utf-8
"""
A table for translate() method to convert a string suitable for placing it
into an url.
This module is part of kiroku project
"""

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
