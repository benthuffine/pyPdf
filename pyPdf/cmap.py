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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
    
    
from generic import *
from pdf import *

import struct
import utils


class CMap(object):
    def __init__(self, data, pdf, *args, **kwargs):
        self.pdf = pdf
        self.map = {}
        self.process_data(data)

    
    def process_data(self, data):
        mode = None
        instructions = ""
        
        for l in data.split("\n"):
            if "beginbfchar" in l:
                mode = "char"
            elif "endbfchar" in l:
                self.process_bfchar_instructions(instructions)
                instructions = ""
                mode = None
            elif "beginbfrange" in l:
                mode = "range"
            elif "endbfrange" in l:
                self.process_bfrange_instructions(instructions)
                instructions = ""
                mode = None
            elif mode == "char" or mode == "range":
                instructions += l
                
    def size(self):
        return len(self.map)
        
    def decode(self, c):
        if not isinstance(c, (int, float)):
            return c 
        return self.map[c]
        
    def build_parser(self, instructions):
        import pdf
        return pdf.PdfFileReader(StringIO(instructions))
        

    def build_stream(self, instructions):
        return StringIO(instructions)
        
    def parse_token(self, stream):
        tok = readObject(stream, self.pdf)
        readNonWhitespace(stream) # move the pointer forward to skip whitespace
        if stream.read(1) != '': # There's still something left in the stream
            stream.seek(-2, 1)
        return tok
        
    def process_bfchar_instructions(self, instructions):
        stream = self.build_stream(instructions)
        find    = str_to_int(self.parse_token(stream))
        replace = str_to_int(self.parse_token(stream))
        while find and replace:
            self.map[find]  = replace
            find            = str_to_int(self.parse_token(stream))
            replace         = str_to_int(self.parse_token(stream))
        
    def process_bfrange_instructions(self, instructions):
        stream = self.build_stream(instructions)
        start   = self.parse_token(stream)
        finish  = self.parse_token(stream)
        to      = self.parse_token(stream)
        while start and finish and to:
            if isinstance(start, basestring) and isinstance(finish, basestring) and isinstance(to, basestring):
                self.bfrange_type_one(start, finish, to)
            elif isinstance(start, basestring) and isinstance(finish, basestring) and isinstance(to, (list, tuple)):
                self.bfrange_type_two(start, finish, to)
            else:
                raise utils.PdfReadError("invalid bfrange section")
            start   = self.parse_token(stream)
            finish  = self.parse_token(stream)
            to      = self.parse_token(stream)
            
    def bfrange_type_one(self, start_code, end_code, dst):
        start_code  = str_to_int(start_code)
        end_code    = str_to_int(end_code)
        dst         = str_to_int(dst)
        
        # add all values in the range to our mapping
        for idx, val in enumerate(range(start_code, (end_code+1))):
            self.map[val] = dst + idx
            #   ensure a single range does not exceed 255 chars
            if idx > 255:
                raise utils.PdfReadError("a CMap bfrange can't exceed 255 chars")
            
    def bfrange_type_two(self, start_code, end_code, dst):
        start_code  = str_to_int(start_code)
        end_code    = str_to_int(end_code)
        from_range = range(start_code, (end_code+1))
        
        #   add all values in the range to our mapping
        for idx, val in enumerate(from_range):
            self.map[val] = str_to_int(dst[idx])
        

def str_to_int(str):
    if not str or len(str) == 0 or len(str) >= 3:
        return None 
    
    if not isinstance(str, ByteStringObject):
        str = encode_pdfdocencoding(str)
    
    if len(str) == 1:
        return struct.unpack("=B", str)[0]
    else:
        return struct.unpack(">H", str)[0]
