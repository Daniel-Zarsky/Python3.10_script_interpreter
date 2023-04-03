import re
import xml.etree.ElementTree as ET
import argparse
import sys
import os


class Read_source:
    def __init__(self, source_file, in_list):
        self.root = None
        self.source = source_file
        self.list = in_list

    def load(self):
        try:
            xml = ET.parse(self.source)
            self.root = xml.getroot()
        except ET.ParseError:
            print("error while reading xml", file=sys.stderr)
            exit(1)  # todo

    def check(self):

        try:
            if self.root.attrib['language'].upper() != "IPPcode23".upper():
                print("error while reading xml", file=sys.stderr)
                exit(1)  # todo
        except KeyError:
            print("error while reading xml", file=sys.stderr)
            exit(1)  # todo

class Interpreter:

    def __init__(self, source_file, input_file):
        self.source = source_file
        self.input = input_file
        self.in_list = []
        self.in_cnt = 0
        self.frame_cnt = []
        self.labels = {}  # dictionary

    def main(self):
        xml = Read_source(self.source, self.in_list)
        xml.load()
        xml.check()


parser = argparse.ArgumentParser(
    prog='interpret.py',
    description='Skript pro interpretaci xml reprezentace kódu IPPcode23',
    epilog='Autor: Daniel Zarsky, xzarsk04')
parser.add_argument('--source', action='store', dest='source_file', help='vstupní soubor s XML reprezentací')
parser.add_argument('--input', action='store', dest='input_file',
                    help='soubor se vstupy pro samotnou interpretaci')
args = parser.parse_args()

if (args.input_file is None) and (args.source_file is None):  # source and input missing
    print("invalid argument or forbidden combination of arguments", file=sys.stderr)
    sys.exit(10)

if args.source_file:
    if not os.path.isfile(args.source_file):
        exit(11)
if args.input_file:
    if not os.path.isfile(args.input_file):
        exit(11)

interpret = Interpreter(args.source_file, args.input_file)
interpret.main()
