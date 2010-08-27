"""
A python port of the ruby pdf-reader library (http://github.com/yob/pdf-reader).  
The liscense for that code copied below.
"""

################################################################################
#
# Copyright (C) 2008 James Healy (jimmy@deefa.com)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
################################################################################

__author__ = "Ben Huffine"
__author_email__ = "ben.huffine@thisismedium.com"

from font import *
from generic import *
import struct, re
import os.path
import utils

class Encoding(object):
    CONTROL_CHARS = range(31)
    UNKNOWN_CHAR = 0x25AF 
    
    def __init__(self, enc, *args, **kwargs):
        if isinstance(enc, dict):
            self._differences = enc.get('/Differences', {})
            self.enc = enc.get('/Encoding', enc.get('/BaseEncoding'))
        else:
            self.enc = enc
            
        self.to_unicode_required = self.unicode_required(self.enc)
        self.unpack = self.get_unpack(self.enc)
        self.map_file = self.get_mapping_file(self.enc)
        
        import font
        self.glyphnames = font.glyphnames()
        self.mapping = {}
        if self.map_file:
            self.load_mapping(self.map_file) 
        
        self._differences = {}


    # set the differences table for this encoding. should be an array in the following format:
    #
    #   [25, :A, 26, :B]
    #
    # The array alternates between a decimal byte number and a glyph name to map to that byte
    #
    # To save space the following array is also valid and equivalent to the previous one
    #
    #   [25, :A, :B]
    def _get_differences(self):
        return self._differences
        
    def _set_differences(self, value):
        if not isinstance(diff, (list, tuple)):
            raise utils.PdfReadError("diff must be an array")
        
        differences = {}
        byte = 0
        for val in diff:
            if isinstance(val, (int, float)):
                byte = int(val)
            else:
                differences[byte] = val
                byte += 1
                
        self._differences = differences
    
    differences = property(_get_differences, _set_differences)
    
    
    # convert the specified string to utf8
    #
    # * unpack raw bytes into codepoints
    # * replace any that have entries in the differences table with a glyph name
    # * convert codepoints from source encoding to Unicode codepoints
    # * convert any glyph names to Unicode codepoints
    # * replace characters that didn't convert to Unicode nicely with something
    #   valid
    # * pack the final array of Unicode codepoints into a utf-8 string
    # * mark the string as utf-8 if we're running on a M17N aware VM
    #

    def unpack_split(self, str):
        l = map(lambda x: ord(encode_pdfdocencoding(x)), list(str))
        return l

    def to_utf8(self, str, tounicode=None):
        ret = map(lambda c: self.differences.has_key(c) and self.differences[c] or c, self.unpack_split(str))
        
        ret = map(lambda num: self.original_codepoint_to_unicode(num, tounicode), ret)
        
        ret = map(lambda c: self.glyphnames.has_key(c) and self.glyphnames[c] or c, ret)
        
        ret = map(lambda c: (not c or not isinstance(c, (int, float)) and self.UNKNOWN_CHAR or c), ret)
        
        ret = ''.join(map(lambda c: unichr(c), ret))
        
        return TextStringObject(ret)
        
    def original_codepoint_to_unicode(self, cp, tounicode=None):
        if tounicode:
            code = tounicode.decode(cp)
            if code:
                return code
        
        if tounicode or (not tounicode and self.to_unicode_required):
            return self.UNKNOWN_CHAR
        elif self.mapping.has_key(cp) and self.mapping[cp]:
            return self.mapping[cp]
        elif cp in self.CONTROL_CHARS:
            return self.UNKNOWN_CHAR
        else:
            return cp
            
    def get_unpack(self, enc):
        if enc == "Identity-H" or enc == "UTF16Encoding":
            return ">H"
        else:
            return "=B"
        
    def get_mapping_file(self, enc):
        dir_name = os.path.dirname(__file__)
        if not enc:
            return "%s/encodings/standard.txt" % dir_name 
        files = {
            "/Identity-H":           None,
            "/MacRomanEncoding":     "%s/encodings/mac_roman.txt" % dir_name,
            "/MacExpertEncoding":    "%s/encodings/mac_expert.txt" % dir_name,
            "/PDFDocEncoding":       "%s/encodings/pdf_doc.txt" % dir_name,
            "/StandardEncoding":     "%s/encodings/standard.txt" % dir_name,
            "/SymbolEncoding":       "%s/encodings/symbol.txt" % dir_name,
            "/UTF16Encoding":        None,
            "/WinAnsiEncoding":      "%s/encodings/win_ansi.txt" % dir_name,
            "/ZapfDingbatsEncoding": "%s/encodings/zapf_dingbats.txt" % dir_name
        }
        
        if files.has_key(enc):
            return files[enc]
        else:
            raise utils.PdfReadError("%s is not currently a supported encoding" % enc)
            
    def unicode_required(self, enc):
        return (enc == "Identity-H")
        
    def has_mapping(self):
        return (len(self.mapping) > 0)
        
    def load_mapping(self, file):
        if self.has_mapping():
            return 
        
        encoding_re = re.compile(r'/([0-9A-Za-z]+);([0-9A-F]{4})/')
        f = open(file, "r")
        try:
            for line in f:
                m = encoding_re.match(line)
                if m:
                    single_byte, unicode_val = m.groups()
                    if single_byte:
                        self.mapping[int(single_byte, 16)] = int(unicode_val, 16) 
        finally: 
            f.close()
        