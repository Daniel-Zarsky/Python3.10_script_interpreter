import re
import xml.etree.ElementTree as ET
import argparse
import sys
import os


class Variable:
    def __init__(self, frame, name):
        self.value = None
        self.frame = frame
        self.name = name
        self.type = None

    def get_frame(self):  # check when reading value from input
        return self.frame

    def get_value(self):  # check when reading value from input
        if self.value is None:
            print("value undefined", file=sys.stderr)
            exit(56)
        return self.value

    def get_type(self):
        return self.type

    def get_name(self):  # check when reading value from input
        return self.name

    def set_value(self, value, type):
        self.value = value
        if type is None:
            if re.match(r'^[0-9]+$', str(value)):
                self.type = 'int'

            elif re.match(r'^(true|false)$', str(value)):
                self.type = 'bool'

            elif re.match(r'^(nil)$', str(value)):
                self.type = 'nil'

            else:
                self.type = 'string'
        else:
            self.type = type


class Frames:
    def __init__(self):
        self.local = []
        self.temp = None
        self.glob = {}
        self.defined = {}

    def debug(self):
        print('temp')
        print(self.temp)
        print('glob')
        print(self.glob)
        print('top local')
        print(self.local)

    def createframe(self):
        self.temp = {}

    def add_to_temp(self, variable):
        if self.temp is None:
            print("empty temporary", file=sys.stderr)
            exit(55)

        self.defined[variable.name] = variable
        self.temp[variable.name] = variable

    # print(self.temp)

    def add_to_glob(self, variable):

        self.defined[variable.name] = variable
        self.glob[variable.name] = variable

    def pushframe(self):

        if self.temp is None:
            print("empty temporary", file=sys.stderr)
            exit(55)

        self.local.insert(0, self.temp)
        self.temp = None

    def popframe(self):
        if len(self.local) == 0:
            print("empty local", file=sys.stderr)
            exit(55)

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
            i += 1

        return False

    def can_access(self, opcode, name, frame):

        if opcode == 'DEFVAR' or opcode == 'TYPE':
            return True
        else:

            if frame == 'GF':
                if name in self.glob:
                    return True
                else:
                    return False

            elif frame == 'LF':
                if len(self.local) > 0:
                    if name in self.local[0]:
                        return True
                    else:
                        return False
                else:
                    exit(55)
            elif frame == 'TF':
                if self.temp is None:
                    print('TF after push', file=sys.stderr)
                    exit(55)

                if name in self.temp:
                    return True
                else:
                    return False
            else:
                print("wrong frame can_access", file=sys.stderr)
                exit(32)  # todo

    def get_value(self, name, frame):
        if frame == 'GF':

            if name not in self.glob:
                print("value undefined", file=sys.stderr)
                exit(55)

            return self.glob[name].get_value()
        elif frame == 'LF':
            if len(self.local) > 0:
                if name not in self.local[0]:
                    print("value undefined", file=sys.stderr)
                    exit(54)
                else:
                    return self.local[0][name].get_value()
            else:
                print("wrong frame", file=sys.stderr)
                exit(54)

        elif frame == 'TF':
            if self.temp is not None:
                if name not in self.temp:
                    print("wrong frame or temporary not exists", file=sys.stderr)
                    exit(54)
                else:
                    return self.temp[name].get_value()
            else:
                print("wrong frame or temporary not exists", file=sys.stderr)
                exit(55)

        else:
            print("wrong frame get value", file=sys.stderr)
            exit(32)  # todo

    def get_type(self, name, frame):
        if frame == 'GF':
            return self.glob[name].get_type()
        elif frame == 'LF':
            return self.local[0][name].get_value()
        elif frame == 'TF':
            return self.temp[name].get_value()

    def set_value(self, frame, name, value, type):

        if frame == 'GF':
            if name in self.glob:
                self.glob[name].set_value(value, type)
            else:
                exit(54)
        elif frame == 'LF':
            if name in self.local:
                self.local[0][name].set_value(value, type)
            else:
                exit(54)
        elif frame == 'TF':
            if self.temp is not None:
                if name in self.temp:
                    self.temp[name].set_value(value, type)
                else:
                    exit(54)
            else:
                print("temporary not exists", file=sys.stderr)
                exit(55)  # todo
        else:
            print("wrong frame set value", file=sys.stderr)
            exit(32)  # todo


class Operand:
    def __init__(self, type, value, frame):
        self.type = type
        self.value = value
        self.frame = frame


class Instruction:
    def __init__(self, order, opcode, operands, frames, labels, input_file, datastack, jumper, input):
        self.order = order
        self.opcode = opcode
        self.operands = operands
        self.datastack = datastack
        self.frames = frames
        self.labels = labels
        self.input = input_file
        self.jumper = jumper
        self.input = input
        self.expected = None  # expected types of arguments

    def check_operands(self):
        # self.debug()

        op_count = 0
        for j in self.operands:
            if j is not None:
                op_count += 1

        if op_count != len(self.expected):
            print("wrong operand count", file=sys.stderr)
            exit(32)

        if self.operands[0] is None and (self.operands[1] is not None or self.operands[2] is not None):
            print("missing argument", file=sys.stderr)
            exit(32)

        for o in self.operands:
            if o is not None:
                if o.type == 'var' and (not self.frames.can_access(self.opcode, o.value, o.frame)):
                    # print('problem here')

                    exit(54)

                if o.type == 'string':

                    if o.value is  None:
                        o.value = ''
                    print("string before processing " + o.value, file=sys.stderr)

                    o.value = replace_unicode_escape_sequences(o.value)
                    print("string after processing" + o.value, file=sys.stderr)

    def debug(self):
        print(self.opcode, end=" ", file=sys.stderr)
        print(self.order, file=sys.stderr)
        for i in self.operands:
            if i is not None:
                print(i.type, end=" ", file=sys.stderr)
                print(i.frame, end=" ", file=sys.stderr)
                print(i.value, file=sys.stderr)

    def get_op_val(self, number):
        if self.operands[number] is not None:
            if self.operands[number].type == 'var':
                value = self.frames.get_value(self.operands[number].value, self.operands[number].frame)
            else:
                value = self.operands[number].value

            return value
        else:
            print("wrong operand number ", file=sys.stderr)
            exit(55)  # todo

    def get_op_type(self, number):
        if self.operands[number] is not None:
            if self.operands[number].type == 'var':
                type = self.frames.get_type(self.operands[number].value, self.operands[number].frame)
            else:
                type = self.operands[number].type

            return type
        else:
            print("wrong operand number ", file=sys.stderr)
            exit(55)  # todo

    def execute(self):
        match self.opcode.upper():
            case 'MOVE':

                self.expected = ['var', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                type1 = self.get_op_type(1)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, value1, type1)

                self.jumper.current += 1

            case 'CREATEFRAME':
                # print('xreatefrafe')
                self.expected = []
                self.check_operands()
                self.frames.createframe()
                self.jumper.current += 1

            case 'POPFRAME':
                self.expected = []
                self.check_operands()
                self.frames.popframe()
                self.jumper.current += 1

            case 'PUSHFRAME':

                self.expected = []
                self.check_operands()
                self.frames.pushframe()
                self.jumper.current += 1

            case 'DEFVAR':

                self.expected = ['var']
                self.check_operands()
                var = Variable(self.operands[0].frame, self.operands[0].value)
                # print(var.value)
                if not self.frames.exists(self.operands[0].value):
                    if var.frame == 'GF':
                        self.frames.add_to_glob(var)
                    elif var.frame == 'TF' and self.frames.temp is not None:
                        if var not in self.frames.temp:
                            self.frames.add_to_temp(var)
                        else:
                            exit(52)
                    else:
                        print("error can add var only to tf or gf ", file=sys.stderr)
                        exit(56)  # todo
                else:
                    exit(52)
                self.jumper.current += 1

            case 'CALL':
                self.expected = ['label']
                self.check_operands()
                if self.operands[0].type != 'label':
                    exit(53)

                value1 = self.operands[0].value  # get label name

                where_to_jump_back = self.jumper.current + 1  # where will we continue after return
                self.jumper.jump_back.insert(0, where_to_jump_back)  # STORE IT IN STACK
                if value1 not in self.jumper.labels:
                    print("non existing label", file=sys.stderr)
                    exit(52)

                self.jumper.current = self.jumper.labels[value1]  # SET CURRENT TO LABEL ORDER VALUE

            case 'RETURN':
                self.expected = []
                self.check_operands()

                if len(self.jumper.jump_back) == 0:
                    print("empty calling stack", file=sys.stderr)
                    exit(56)

                self.jumper.current = self.jumper.jump_back[0]  # JUMP BACK
                del self.jumper.jump_back[0]  # poP IT

            case 'PUSHS':
                self.expected = ['symb']
                self.check_operands()
                if self.operands[0].type == 'var':  # pushing variable
                    value = self.frames.get_value(self.operands[0].value,
                                                  self.operands[0].frame)  # get value of variable
                    self.datastack.insert(0, value)
                else:
                    self.datastack.insert(0, self.operands[0].value)  # push directly value of constant

                self.jumper.current += 1

            case 'POPS':
                self.expected = ['var']
                self.check_operands()
                if len(self.datastack) != 0:
                    self.frames.set_value(self.operands[0].frame, self.operands[0].value,
                                          self.datastack[0], None)
                    del self.datastack[0]
                else:
                    exit(56)

                self.jumper.current += 1

            case 'ADD':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'int' or type1 is None:
                    exit(53)

                result = int(value1) + int(value2)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'SUB':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'int' or type1 is None:
                    exit(53)

                result = int(value1) - int(value2)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'MUL':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'int' or type1 is None:
                    exit(53)

                result = int(value1) * int(value2)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'IDIV':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)
                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'int' or type1 is None:
                    exit(53)

                if int(value2) == 0:
                    exit(57)

                result = int(value1) // int(value2)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'LT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if (type1 != type2):
                    exit(53)


                if (type1 == 'nil') or (type2 == 'nil'):
                    exit(53)

                if (type1 == 'int'):
                    result = int(value1) < int(value2)
                else:
                    result = value1 < value2

                if result is True:
                    result = 'true'
                else:
                    result = 'false'
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'bool')

                self.jumper.current += 1

            case 'GT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)
                print(f"value 1 {value1} ", file=sys.stderr)
                print(f"value 2 {value2} ", file=sys.stderr)
                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if (type1 != type2):
                    exit(53)

                if (type1 == 'nil') or (type2 == 'nil'):
                    exit(53)

                if (type1 == 'int'):
                    result = int(value1) > int(value2)
                else:
                    result = value1 > value2

                if result is True:
                    result = 'true'
                else:
                    result = 'false'
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'bool')

                self.jumper.current += 1

            case 'EQ':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if (type1 != type2) and (type1 != 'nil' and type2 != 'nil'):
                    exit(53)

                if type1 == 'int' or type2 == 'int':
                    if (type1 == 'nil') or (type2 == 'nil'):
                        result = False
                    else:
                        result = int(value1) == int(value2)
                else:
                    result = value1 == value2

                if result is True:
                    result = 'true'
                else:
                    result = 'false'
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'bool')

                self.jumper.current += 1

            case 'AND':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'bool':
                    exit(53)

                if value1 == 'true':
                    value1 = True
                else:
                    value1 = False

                if value2 == 'true':
                    value2 = True
                else:
                    value2 = False

                result = value1 and value2
                if result is True:
                    result1 = 'true'
                else:
                    result1 = 'false'
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result1, 'bool')

                self.jumper.current += 1

            case 'OR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != type2 or type1 != 'bool':
                    exit(53)

                if value1 == 'true':
                    value1 = True
                else:
                    value1 = False

                if value2 == 'true':
                    value2 = True
                else:
                    value2 = False

                result = value1 or value2
                if result is True:
                    result1 = 'true'
                else:
                    result1 = 'false'

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result1, 'bool')

                self.jumper.current += 1

            case 'NOT':
                self.expected = ['var', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                type1 = self.get_op_type(1)
                if type1 != 'bool':
                    exit(53)

                if value1 == 'true':
                    value1 = True
                else:
                    value1 = False
                result = not value1
                if result is True:
                    result1 = 'true'
                else:
                    result1 = 'false'
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result1, 'bool')

                self.jumper.current += 1

            case 'INT2CHAR':
                self.expected = ['var', 'symb']
                self.check_operands()
                value1 = self.get_op_val(1)
                type1 = self.get_op_type(1)
                if type1 != 'int':
                    exit(53)

                if int(value1) < 0 or int(value1) > 128:
                    exit(58)

                try:
                    result = chr(int(value1))
                except ValueError:
                    print("value out of range", file=sys.stderr)
                    exit(53)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'string')

                self.jumper.current += 1

            case 'STRI2INT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != 'string' or type2 != 'int':
                    exit(53)

                if int(value2) >= len(value1) or int(value2) < 0:
                    print("value out of range", file=sys.stderr)
                    exit(58)

                char = value1[int(value2)]
                try:
                    result = ord(char)
                except ValueError:
                    print("value out of range", file=sys.stderr)
                    exit(53)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'READ':
                self.expected = ['var', 'type']
                self.check_operands()

                type2 = self.operands[1].value

                if self.input is None:
                    line = input(sys.stdin.buffer)
                else:
                    line = self.input[self.jumper.input_index]
                    self.jumper.input_index += 1

                print(f"line is  {self.jumper.input_index}", file=sys.stderr)
                print(f"line is  {line}", file=sys.stderr)
                print(f"type is  {type2}", file=sys.stderr)

                if type == 'int':
                    result = int(line)
                elif type == 'bool':
                    if line != 'true':
                        result = 'false'
                    else:
                        result = line
                else:
                    result = line

                print(f"result is  {result}", file=sys.stderr)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, type2)


                self.jumper.current += 1

            case 'WRITE':

                self.expected = ['symb']
                self.check_operands()

                value = self.get_op_val(0)

                print(value, end="")

                self.jumper.current += 1

            case 'CONCAT':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != 'string' or type2 != 'string':
                    exit(53)
                if value1 is None:
                    value1 = ''
                if value2 is None:
                    value2 = ''
                result = value1 + value2
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'string')

                self.jumper.current += 1

            case 'STRLEN':
                self.expected = ['var', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)

                type1 = self.get_op_type(1)
                if type1 != 'string':
                    exit(53)

                if value1 is None or value1 == '':
                    result = 0
                else:
                    result = len(value1)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'int')

                self.jumper.current += 1

            case 'GETCHAR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != 'string' or type2 != 'int':
                    exit(53)

                if int(value2) >= len(value1) or int(value2) < 0:
                    print("value out of range", file=sys.stderr)
                    exit(58)

                result = value1[int(value2)]
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, 'string')

                self.jumper.current += 1

            case 'SETCHAR':
                self.expected = ['var', 'symb', 'symb']
                self.check_operands()

                var = self.get_op_val(0)
                symb1 = self.get_op_val(1)
                symb2 = self.get_op_val(2)

                type0 = self.get_op_type(0)
                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if type1 != 'int' or type2 != 'string' or type0 != 'string':
                    exit(53)

                if int(symb1) >= len(var) or int(symb1) < 0 or symb2 == '':
                    print("value out of range", file=sys.stderr)
                    exit(58)

                posn = int(symb1)
                nc = symb2[0]
                var = var[:posn] + nc + var[posn + 1:]
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, var, 'string')

                self.jumper.current += 1

            case 'TYPE':
                self.expected = ['var', 'symb']
                self.check_operands()

                var = self.get_op_val(1)  # variable unused on purpose
                type1 = self.get_op_type(1)

                self.frames.set_value(self.operands[0].frame, self.operands[0].value, type1, 'string')

                self.jumper.current += 1

            case 'LABEL':

                self.expected = ['label']
                self.check_operands()
                self.jumper.current += 1

            case 'JUMP':
                self.expected = ['label']
                self.check_operands()

                label_name = self.get_op_val(0)

                if label_name not in self.jumper.labels:
                    print("non existing label", file=sys.stderr)
                    exit(52)

                self.jumper.current = self.jumper.labels[label_name]

            case 'JUMPIFEQ':
                self.expected = ['label', 'symb', 'symb']
                self.check_operands()

                label_name = self.operands[0].value
                value1 = self.get_op_val(1)
                value2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if (type1 != type2) and (type1 != 'nil' and type2 != 'nil'):
                    exit(53)

                if label_name not in self.jumper.labels:
                    print("non existing label", file=sys.stderr)
                    exit(52)


                if type1 == 'int' or type2 == 'int':
                    if (type1 == 'nil') or (type2 =='nil'):
                        result = False
                    else:
                        result = int(value1) == int(value2)
                else:
                    result = value1 == value2
                if result:
                    self.jumper.current = self.jumper.labels[label_name]
                else:
                    self.jumper.current += 1

            case 'JUMPIFNEQ':
                self.expected = ['label', 'symb', 'symb']
                self.check_operands()

                label_name = self.operands[0].value
                symb1 = self.get_op_val(1)
                symb2 = self.get_op_val(2)

                type1 = self.get_op_type(1)
                type2 = self.get_op_type(2)

                if (type1 != type2) and (type1 != 'nil' and type2 != 'nil'):
                    exit(53)

                if label_name not in self.jumper.labels:
                    print("non existing label", file=sys.stderr)
                    exit(52)

                if symb1 != symb2:

                    self.jumper.current = self.jumper.labels[label_name]
                else:
                    self.jumper.current += 1

            case 'EXIT':
                self.expected = ['symb']
                self.check_operands()

                value1 = self.get_op_val(0)
                type1 = self.get_op_type(0)

                if type1 != 'int':
                    exit(53)

                if int(value1) < 0 or int(value1) > 49:
                    exit(57)

                os._exit(int(value1))

            case 'DPRINT':
                self.expected = ['symb']
                self.check_operands()

                value1 = self.get_op_val(0)
                print(value1, file=sys.stderr)
                self.jumper.current += 1

            case 'BREAK':
                self.expected = []
                self.check_operands()
                self.jumper.current += 1

            case _:
                print("wrong opcode", file=sys.stderr)
                exit(32)


class Read_source:
    def __init__(self, source_file, frames, labels, datastack, input_file, jumper, input):
        self.root = None
        self.source = source_file
        self.input_file = input_file
        self.frames = frames
        self.labels = labels
        self.datastack = datastack
        self.jumper = jumper
        self.input = input

    def load(self):
        source_file = self.source
        print(f"source {source_file}", file=sys.stderr)

        if self.source is None:
            try:
                parser = ET.parse(sys.stdin)
            except ET.ParseError:
                print("error while reading xml", file=sys.stderr)
                exit(31)
        else:

            try:
                parser = ET.parse(str(self.source))
            except ET.ParseError:
                print("error while reading xml here ", file=sys.stderr)
                exit(31)

        self.root = parser.getroot()

        return self.root

    def check(self):

        try:
            if self.root.attrib['language'].upper() != "IPPcode23".upper():  # name a description nekotroluju kdyz
                # jsou volitelne
                print("error while reading xml", file=sys.stderr)
                exit(32)
        except KeyError:
            print("error while reading xml v hlavicce", file=sys.stderr)
            exit(31)

        for child in self.root:
            if child.tag != 'instruction':
                print("chyba v xml", file=sys.stderr)
                exit(32)

            child_at = child.attrib
            if len(child_at) != 2 or ('opcode' not in child_at or 'order' not in child_at):
                print("chyba v xml", file=sys.stderr)
                exit(32)

            if not re.match(r'^[1-9]\d*$', child.attrib['order']):
                print("negative order", file=sys.stderr)
                exit(32)

            for number, arg in enumerate(child, 1):
                try:
                    if not re.match('^arg[123]$', arg.tag) or number > 3:
                        print("spatny argument", file=sys.stderr)
                        exit(32)
                except KeyError:
                    print("error while checking arguments", file=sys.stderr)
                    exit(31)

    def fill_list(self):

        instruction_list = []
        for child in self.root:

            opcode = child.attrib['opcode']
            operands = [None] * 3
            order = int(child.attrib['order'])
            for i, subchild in enumerate(child, 1):
                if subchild.tag == 'arg1':
                    if subchild.attrib['type'] == 'var':
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
                    exit(31)

            new_int = Instruction(order, opcode, operands, self.frames, self.labels, self.input_file,
                                  self.datastack, self.jumper, self.input)
            instruction_list.append(new_int)

            order_arr = []
            for i in instruction_list:
                if i.order not in order_arr:
                    order_arr.append(i.order)
                else:
                    print("duplicate order", file=sys.stderr)
                    exit(32)

            # instruction_list.sort(key=lambda x: x.order, reverse=False)
            instruction_list = sorted(instruction_list, key=lambda x: x.order, reverse=False)

        right_order = 0
        for j in instruction_list:
            j.order = right_order
            right_order += 1

        return instruction_list


class Jumper:
    def __init__(self):
        self.current = 0
        self.jump_back = []
        self.labels = {}
        self.input_index = 0

    def extract_labels(self, in_list):
        for i in in_list:
            if i.opcode.upper() == 'LABEL':
                if i.operands[0].value not in self.labels:
                    self.labels[i.operands[0].value] = i.order
                else:
                    print("label redefinition", file=sys.stderr)
                    exit(52)


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
        jumper = Jumper()
        xml = Read_source(self.source, self.frames, self.labels, self.datastack, self.in_list, jumper, self.input)
        xml.load()
        xml.check()
        self.in_list = xml.fill_list()

        jumper.extract_labels(self.in_list)

        # print(jumper.labels)

        while jumper.current < len(self.in_list):

            # self.frames.debug()
            # print(self.datastack)
            instruction = self.in_list[jumper.current]
            # print(instruction.opcode, file=sys.stderr)
            # print(instruction.opcode)
            if instruction is None:
                break
            else:
                # instruction.debug()
                instruction.execute()
def replace_unicode_escape_sequences(s):
    """
    Replaces Unicode escape sequences in a string with their corresponding characters.
    :param s: The input string
    :return: The string with Unicode escape sequences replaced
    """
    import re

    # Regular expression pattern to match Unicode escape sequences
    pattern = r'\\[0-9]{3}'
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
        " ": "",
        "\\": "",
        "#": "",
    }

    def replace_unicode(match):
        """
        Callback function to replace a matched Unicode escape sequence with its corresponding character.
        """
        escape_sequence = match.group(0)
        unicode_char = chr(int(escape_sequence[2:], 10))
        return unicode_char


    # Use regex to find all Unicode escape sequences and replace them
    result = re.sub(pattern, replace_unicode, s)
    for c in result:
        if c in html_escape_table:
            result.replace(c, html_escape_table[c])


    return result


parser = argparse.ArgumentParser(
    prog='interpret.py',
    description='Skript pro interpretaci xml reprezentace kódu IPPcode23',
    epilog='Autor: Daniel Zarsky, xzarsk04')
parser.add_argument('--source', action='store', dest='source_file', help='vstupní soubor s XML reprezentací')
parser.add_argument('--input', action='store', dest='input_file',
                    help='soubor se vstupy pro samotnou interpretaci')
args = parser.parse_args()

input_content = None
lines = None
if args.source_file is not None or args.input_file is not None:
    if args.source_file:
        if not os.path.isfile(args.source_file):
            exit(11)

    if args.input_file is not None:
        if not os.path.isfile(args.input_file):
            exit(11)
        try:
            input_content = open(args.input_file)
        except Exception:
            exit(12)
        try:
            lines = input_content.read().splitlines()
        except EOFError:
            lines = None
            exit(11)

else:
    lines = None
    exit(11)

interpret = Interpreter(args.source_file, lines)
interpret.main()
