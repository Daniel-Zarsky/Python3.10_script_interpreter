import re
import xml.etree.ElementTree as ET
import argparse
import sys
import os


class Variable:
    def __init__(self, frame, name, frames):
        self.value = None
        self.frame = frame
        self.name = name
        self.frames = frames

    def debug(self):
        print(self.frame)
        print(self.name)

    def defined(self):
        if self.value is None:
            return False

    def get_frame(self):  # check when reading value from input
        return self.frame

    def get_value(self):  # check when reading value from input
        return self.value

    def get_name(self):  # check when reading value from input
        return self.name

    def set_value(self, value):
        self.value = value


class Frames:
    def __init__(self):
        self.local = []
        self.temp = None
        self.glob = {}

    def create_local_frame(self):
        self.local.insert(0, {})

    def createframe(self):
        self.temp = {}

    def check_temp(self):
        if self.temp is None:
            return False

    def add_to_temp(self, variable):
        self.temp[variable.name] = variable

    def add_to_glob(self, variable):
        self.glob[variable.name] = variable

    def pushframe(self):
        self.local.insert(0, self.temp)

    def popframe(self):
        self.temp = self.local[0]
        del self.local[0]

    def exists(self, name):  # for defvar checking

        if name in self.glob:
            return True

        if self.temp is not None and name in self.temp:
            return True

        i = 0
        while i < len(self.local):
            if name in self.local[i]:
                return True

        return False

    def can_access(self, name):
        if self.temp is not None and name in self.temp:   # in temporary
            return True
        elif name in self.glob:  # in global
            return True
        elif name in self.local: # in the top local frame
            return True
        else:
           return False

    def get_value(self, name, frame):
        if frame == 'GF':
            return self.glob[name]
        elif frame == 'LF':
            return self.local[0][name]
        elif frame == 'TF':
            return self.temp[name]
        else:
            print("wrong frame", file=sys.stderr)
            exit(1)  # todo

    def set_value(self, frame, name, value):
        if frame == 'GT' and name in self.glob:
            self.glob[name].set_value(value)
        elif frame == 'LF' and name in self.local:
            self.local[0][name].set_value(value)
        elif frame == 'TF'  and name in self.temp:
            self.temp[name].set_value(value)
        else:
            print("wrong frame", file=sys.stderr)
            exit(1)  # todo


class Operand:
    def __init__(self, type, value, frame):
        self.type = type
        self.value = value
        self.frame = frame


class Instruction:
    def __init__(self, order, opcode, operands, frames, labels, input_file, in_list, datastack):
        self.order = order
        self.opcode = opcode
        self.operands = operands
        self.datastack = datastack
        self.frames = frames
        self.labels = labels
        self.input = input_file
        self.list = in_list
        self.expected = None  # expected types of arguments

    def check_operands(self):
        # self.debug()
        i = 0
        for o in self.operands:
            if o is not None:
                if self.expected[i] == 'symb' and (
                        self.operands[i].type == 'int' or self.operands[i].type == 'string'
                        or self.operands[i].type == 'bool' or self.operands[i].type == 'var'
                        or self.operands[i].type == 'nil'):
                    continue

                if self.expected[i] != self.operands[i].type:
                    print("wrong operand type", file=sys.stderr)
                    exit(1)  # todo

                if (self.opcode != 'DEFVAR' or self.opcode != 'TYPE') and o.type == 'var' and not self.frames.can_access(o.value):
                    print("can not access the variable in operand", file=sys.stderr)  # no access to first
                    exit(1)  # todo

    def debug(self):
        print(self.opcode)
        print(self.order)
        for op in self.operands:
            if op is not None:
                print(op.frame)
                print(op.type)
                print(op.value)

    def get_op_val(self, number):
        if self.operands[number].type == 'var':
            value = self.frames.get_value(self.operands[number].value, self.operands[1].frame)
        else:
            value = self.operands[number].value

        return value

    def execute(self):
        match self.opcode.upper():
            case 'MOVE':
                self.expected = ['var', 'symb']
                self.check_operands()
                if self.operands[1].type == 'var':
                    value = self.frames.get_value(self.operands[0].value, self.operands[0].frame)
                    self.frames.set_value(self.operands[0].frame, self.operands[0].value, value)  # asign variable to the first operand
                else:
                    self.frames.set_value(self.operands[0].frame, self.operands[0].value, self.operands[1].value)  # asign constant to first operand

            case 'CREATEFRAME':
                self.expected = []
                self.check_operands()
                self.frames.createframe()

            case 'POPFRAME':
                self.expected = []
                self.check_operands()
                self.frames.popframe()

            case 'PUSHFRAME':
                self.expected = []
                self.check_operands()
                self.frames.pushframe()

            case 'DEFVAR':
                self.expected = ['var']
                self.check_operands()

                if not self.frames.exists(self.operands[0].value):
                    var = Variable(self.operands[0].frame, self.operands[0].value, self.frames)

                    if var.frame == 'GF':
                        self.frames.add_to_glob(var)
                    elif var.frame == 'TF':
                        self.frames.add_to_temp(var)
                    else:
                        print("error can add v ar only to tf or gf ", file=sys.stderr)
                        exit(1)  # todo

            case 'CALL':
                self.expected = ['label']
                self.check_operands()

            case 'RETURN':
                self.expected = []
                self.check_operands()

            case 'PUSHS':
                self.expected = ['symb']
                self.check_operands()
                if self.operands[0].type == 'var':  # pushing variable
                    value = self.frames.get_value(self.operands[0].value, self.operands[0].frame)  # get value of variable
                    self.datastack.insert(0, value)
                else:
                    self.datastack.insert(0, self.operands[0].value)  # push directly value of constant
            case 'POPS':
                self.expected = ['var']
                self.check_operands()
                if len(self.datastack) != 0:
                    del self.datastack[0]

            case 'ADD':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 + value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'SUB':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 - value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'MUL':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1*value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'IDIV':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 // value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'LT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                if self.operands[1].type =='nil' or self.operands[2].type =='nil':
                    print("nil in lower", file=sys.stderr)
                    exit(53)

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 < value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'GT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                if self.operands[1].type == 'nil' or self.operands[2].type == 'nil':
                    print("nil in greater", file=sys.stderr)
                    exit(53)

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 > value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'EQ':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 == value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'AND':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                if self.operands[1].type != 'bool' or self.operands[2].type != 'bool':
                    print("nil in greater", file=sys.stderr)
                    exit(53)

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 and value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'OR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                if self.operands[1].type != 'bool' or self.operands[2].type != 'bool':
                    print("nil in greater", file=sys.stderr)
                    exit(53)

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                result = value1 or value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'NOT':
                self.expected = ['var', 'symb']
                self.check_operands()

                if self.operands[1].type != 'bool':
                    print("nil in greater", file=sys.stderr)
                    exit(53)

                value1 = self.get_op_val(1)

                result = not value1
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'INT2CHAR':
                self.expected = ['var', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)

                try:
                    result = chr(value1)
                except ValueError:
                    print("value out of range", file=sys.stderr)
                    exit(53)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'STRI2INT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                if value2 >= len(value1):
                    print("value out of range", file=sys.stderr)
                    exit(53)

                char = value1[value2]
                try:
                    result = ord(char)
                except ValueError:
                    print("value out of range", file=sys.stderr)
                    exit(53)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'READ':
                self.expected = ['var', 'type']
                self.check_operands()

            case 'WRITE':
                self.expected = ['symb']
                self.check_operands()

            case 'CONCAT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                if type(value1) is not str or type(value2) is not str:
                    print("wrong value for concat", file=sys.stderr)
                    exit(53)

                result = value1 + value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'STRLEN':
                self.expected = ['var', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)

                result = len(value1)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)


            case 'GETCHAR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                if value2 >= len(value1):
                    print("value out of range", file=sys.stderr)
                    exit(53)

                result = value1[value2]
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result)

            case 'SETCHAR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                var = self.get_op_val(0)
                symb1 = self.get_op_val(1)
                symb2 = self.get_op_val(2)

                if symb1 >= len(var) or symb2 is None:
                    print("value out of range", file=sys.stderr)
                    exit(53)

                var[symb1] = symb2[0]
                self.frames.set_value(self.operands[0].frame, self.operands[0].value,var)

            case 'TYPE':
                self.expected = ['var', 'symb']
                self.check_operands()



            case 'LABEL':
                self.expected = ['label']
                self.check_operands()

            case 'JUMP':
                self.expected = ['label']
                self.check_operands()

            case 'JUMPIFEQ':
                self.expected = ['label', 'symb', 'symb']
                self.check_operands()

            case 'JUMPIFNEQ':
                self.expected = ['label', 'symb', 'symb']
                self.check_operands()

            case 'EXIT':
                self.expected = ['symb']
                self.check_operands()

            case 'DPRINT':
                self.expected = ['symb']
                self.check_operands()

            case 'BREAK':
                self.expected = []
                self.check_operands()


class Read_source:
    def __init__(self, source_file, frames, labels, datastack, input_file):
        self.root = None
        self.source = source_file
        self.input_file = input_file
        self.frames = frames
        self.labels = labels
        self.datastack = datastack

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
                    if subchild.attrib['type'] =='var':
                        if '@' in subchild.text:
                            frame, value = subchild.text.split('@')
                        else:
                            # Handle the case when '@' is not found, e.g. assign default values
                            frame = None
                            value = None
                        operands[0] = Operand(subchild.attrib['type'], value, frame)
                    else:
                        operands[0] = Operand(subchild.attrib['type'], subchild.text, None)

                elif subchild.tag == 'arg2':
                    if subchild.attrib['type'] == 'var':
                        if '@' in subchild.text:
                            frame, value = subchild.text.split('@')
                        else:
                            # Handle the case when '@' is not found, e.g. assign default values
                            frame = None
                            value = None
                        operands[1] = Operand(subchild.attrib['type'], value, frame)
                    else:
                        operands[1] = Operand(subchild.attrib['type'], subchild.text, None)
                elif subchild.tag == 'arg3':
                    if subchild.attrib['type'] == 'var':
                        if '@' in subchild.text:
                            frame, value = subchild.text.split('@')
                        else:
                            # Handle the case when '@' is not found, e.g. assign default values
                            frame = None
                            value = None
                        operands[2] = Operand(subchild.attrib['type'], value, frame)
                    else:
                        operands[2] = Operand(subchild.attrib['type'], subchild.text, None)
                else:
                    print("error while loading operands", file=sys.stderr)
                    exit(1)

            new_int = Instruction(order, opcode, operands, self.frames,  self.labels, self.input_file, instruction_list, self.datastack,)
            instruction_list.append(new_int)
        instruction_list.sort(key=lambda x: x.order)
        return instruction_list


class Interpreter:

    def __init__(self, source_file, input_file):
        self.source = source_file
        self.input = input_file
        self.in_list = []
        self.in_cnt = 0
        self.frames = Frames()
        self.datastack = []
        self.labels = []

    def main(self):
        xml = Read_source(self.source, self.frames, self.labels, self.datastack, self.in_list)
        xml.load()
        xml.check()
        self.in_list = xml.fill_list()
        i = 0
        while i < len(self.in_list):
            #print(self.frames.glob)
            instruction = self.in_list[i]
            if instruction is None:
                break
            else:
                i = i + 1
                instruction.execute()


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
