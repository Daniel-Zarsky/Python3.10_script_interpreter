import re
import xml.etree.ElementTree as ET
import argparse
import sys
import os


class Operand:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def get_type(self):
        return self.type

    def get_value(self):
        return self.value


class Instruction:
    def __init__(self, order, opcode, operands, frame_stack, labels, input_file, in_list):
        self.order = order
        self.opcode = opcode
        self.operands = operands
        self.frames = frame_stack
        self.labels = labels
        self.input = input_file
        self.list = in_list
        self.expected = None  # expected types of arguments

    def check_operands(self):

        for i, o in enumerate(self.operands, 1):
            if self.expected[i] != self.operands[i].type:
                print("wrong operand type", file=sys.stderr)
                exit(1)  # todo

    def debug(self):
        for op in self.operands:
            if op is not None:
                print(op.type)
                print(op.value)


class Read_source:
    def __init__(self, source_file, stack, labels, input_file):
        self.root = None
        self.source = source_file
        self.frame_stack = stack
        self.labels = labels
        self.input_file = input_file

    def load(self):
        try:
            xml = ET.parse(self.source)
            self.root = xml.getroot()
        except ET.ParseError:
            print("error while reading xml", file=sys.stderr)
            exit(1)  # todo

    def check(self):

        try:
            if self.root.attrib['language'].upper() != "IPPcode23".upper():  # name a description nekotroluju kdyz
                # jsou volitelne
                print("error while reading xml", file=sys.stderr)
                exit(1)  # todo
        except KeyError:
            print("error while reading xml", file=sys.stderr)
            exit(1)  # todo

        for child in self.root:
            if child.tag != 'instruction':
                print("chyba v xml", file=sys.stderr)
                exit(1)

            child_at = child.attrib
            if len(child_at) != 2 or ('opcode' not in child_at or 'order' not in child_at):
                print("chyba v xml", file=sys.stderr)
                exit(1)

            for number, arg in enumerate(child, 1):
                try:
                    if not re.match('^arg[123]$', arg.tag) or number > 3:
                        print("spatny argument", file=sys.stderr)
                        exit(1)
                except KeyError:
                    print("error while checking arguments", file=sys.stderr)
                    exit(1)  # todo

    def fill_list(self):

        instruction_list = []
        for child in self.root:
            opcode = child.attrib['opcode']
            operands = [None] * 3
            order = child.attrib['order']
            for i, subchild in enumerate(child, 1):
                if subchild.tag == 'arg1':
                    operands[0] = Operand(subchild.attrib['type'], subchild.text)
                elif subchild.tag == 'arg2':
                    operands[1] = Operand(subchild.attrib['type'], subchild.text)
                elif subchild.tag == 'arg3':
                    operands[2] = Operand(subchild.attrib['type'], subchild.text)
                else:
                    print("error while loading operands", file=sys.stderr)
                    exit(1)

                new_int = Instruction(order, opcode, operands, self.frame_stack, self.labels, self.input_file,
                                      instruction_list)
                instruction_list.append(new_int)

        sorted_instructions = sorted(instruction_list, key=lambda x: x.order, reverse=False)

        return sorted_instructions


class Interpreter:

    def __init__(self, source_file, input_file):
        self.source = source_file
        self.input = input_file
        self.in_list = []
        self.in_cnt = 0
        self.frame_stack = []
        self.labels = {}  # dictionary

    def main(self):
        xml = Read_source(self.source, self.frame_stack, self.labels, self.in_list)
        xml.load()
        xml.check()
        self.in_list = xml.fill_list()
        i = 0
        while i < len(self.in_list):

            instruction = self.in_list[i]
            if instruction is None:
                break
            else:
                i = i + 1
                instruction.debug()


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
