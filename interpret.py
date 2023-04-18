import re
import xml.etree.ElementTree as ET
import argparse
import sys
import os


class Variable:
    """
    Class represents a variable
    General management of variables ensures class Frames
    """
    def __init__(self, frame, name):
        """constructor"""
        self.value = None
        self.frame = frame
        self.name = name
        self.type = None

    def get_value(self):
        """"returns value of variable"""
        if self.value is None:
            print("value undefined", file=sys.stderr)
            exit(56)
        return self.value

    def get_type(self):
        """"returns type of variable"""
        return self.type

    def set_value(self, value, type):
        """"set value of variable based on it's type"""
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
    """
    Class Frames is in charge of storing variables

    """
    def __init__(self):
        """constructor"""
        self.local = []
        self.temp = None
        self.glob = {}
        self.locals = 0

    def createframe(self):
        """initializes temporary frame"""
        self.temp = {}

    def add_to_temp(self, variable):
        """adds variable to temporary frame"""
        if self.temp is None:
            print("empty temporary", file=sys.stderr)
            exit(55)

        self.temp[variable.name] = variable

    def add_to_glob(self, variable):
        """adds variable to global frame"""

        self.glob[variable.name] = variable

    def add_to_local(self, variable):
        """adds variable to local frame"""

        new_var = {variable.name: variable}
        self.local[0].update(new_var)

    def pushframe(self):
        """moves temporary frame to local frame"""
        if self.temp is None:
            print("empty temporary", file=sys.stderr)
            exit(55)

        self.locals += 1
        self.local.insert(0, self.temp)
        self.temp = None

    def popframe(self):
        """moves top local frame to temporary frame """
        if len(self.local) == 0:
            print("empty local", file=sys.stderr)
            exit(55)

        self.locals -= 1
        self.temp = self.local[0]
        del self.local[0]

    def exists(self, name, frame):
        """checks whether the variable was declared """

        if frame == 'GF':
            if name in self.glob:
                print("je v globalu ", file=sys.stderr)
                return True

        if frame == 'TF':
            if self.temp is not None and name in self.temp:
                print("je v temporary ", file=sys.stderr)
                return True
        if frame == 'LF':
            if len(self.local) > 0:
                if name in self.local[0]:
                    return True

        return False

    def can_access(self, opcode, name, frame):
        """checks whether the caller of this function can access the variable """
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
                exit(32)

    def get_value(self, name, frame):
        """ returns value of a variable """
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
            exit(32)

    def get_type(self, name, frame):
        """returns type of variable """

        if frame == 'GF':
            return self.glob[name].get_type()
        elif frame == 'LF':
            return self.local[0][name].get_type()
        elif frame == 'TF':
            return self.temp[name].get_type()

    def set_value(self, frame, name, value, type):
        """ set value of a variable """
        if frame == 'GF':
            if len(self.glob) != 0:
                if name in self.glob:
                    self.glob[name].set_value(value, type)
                else:
                    print("variale not in global", file=sys.stderr)
                    exit(54)

        elif frame == 'LF':
            if len(self.local) > 0:
                if name in self.local[0]:
                    self.local[0][name].set_value(value, type)
                else:
                    print("variale not in local", file=sys.stderr)
                    exit(54)

        elif frame == 'TF':
            if self.temp is not None:
                if name in self.temp:
                    self.temp[name].set_value(value, type)
                else:
                    print("variable not in temporary ", file=sys.stderr)
                    exit(54)
            else:
                print("temporary not exists", file=sys.stderr)
                exit(55)
        else:
            print("wrong frame set value", file=sys.stderr)
            exit(32)


class Operand:
    """class represents one operand of an instruction """
    def __init__(self, type, value, frame):
        self.type = type
        self.value = value
        self.frame = frame


class Instruction:
    """class represents instruction of IPPcode23"""
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
        """checks if the operands of an instruction are valid """

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
                    exit(54)

                if o.type == 'string':

                    if o.value is None:
                        o.value = ''
                    print("string before processing " + o.value, file=sys.stderr)

                    o.value = replace_unicode_escape_sequences(o.value)
                    print("string after processing" + o.value, file=sys.stderr)


    def get_op_val(self, number):
        """returns value of an operand"""

        if self.operands[number] is not None:
            if self.operands[number].type == 'var':
                value = self.frames.get_value(self.operands[number].value, self.operands[number].frame)
            else:
                value = self.operands[number].value

            return value
        else:
            print("wrong operand number ", file=sys.stderr)
            exit(55)

    def get_op_type(self, number):
        """returns type of an operand"""
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
        """executes the instruction based on it's opcede and operands"""

        match self.opcode.upper():
            case 'MOVE':

                self.expected = ['var', 'symb']
                self.check_operands()

                value1 = self.get_op_val(1)
                type1 = self.get_op_type(1)
                self.frames.set_value(self.operands[0].frame, self.operands[0].value, value1, type1)

                self.jumper.current += 1

            case 'CREATEFRAME':
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
                if not self.frames.exists(self.operands[0].value, self.operands[0].frame):
                    if var.frame == 'GF':
                        self.frames.add_to_glob(var)
                    elif var.frame == 'TF' and self.frames.temp is not None:
                        if var not in self.frames.temp:
                            self.frames.add_to_temp(var)
                        else:
                            print("found 2 ", file=sys.stderr)
                            exit(52)
                    else:
                        if self.frames.locals > 0:
                            self.frames.add_to_local(var)
                        else:
                            print("found 1 ", file=sys.stderr)
                            exit(55)

                else:
                    print("existuje", file=sys.stderr)
                    exit(52)
                self.jumper.current += 1

            case 'CALL':
                self.expected = ['label']
                self.check_operands()
                if self.operands[0].type != 'label':  # typ je label
                    exit(53)

                value1 = self.operands[0].value  # label existuje
                if value1 not in self.jumper.labels:
                    print("non existing label", file=sys.stderr)
                    exit(52)

                where_to_jump_back = self.jumper.current + 1  # where will we continue after return
                self.jumper.jump_back.insert(0, where_to_jump_back)  # STORE IT IN STACK

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
                    try:
                        line = input(sys.stdin.buffer)
                        if type2 == 'int':
                            if re.match(r'^(-)?[0-9]\d*$', str(line)):
                                result = int(line)
                            else:
                                result = 'nil'
                                type2 = 'nil'
                        elif type2 == 'bool':

                            if re.match(r'^(true)$', str(line), re.IGNORECASE):
                                result = 'true'
                            else:
                                result = 'false'

                        else:
                            result = line

                        print(f"result is  {result}", file=sys.stderr)
                        self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, type2)
                    except EOFError:
                        self.frames.set_value(self.operands[0].frame, self.operands[0].value, 'nil', 'nil')

                else:
                    line = self.input[self.jumper.input_index]
                    if type2 == 'int':
                        if re.match(r'^(-)?[0-9]\d*$', str(line)):
                            result = int(line)
                        else:
                            result = 'nil'
                            type2 = 'nil'
                    elif type2 == 'bool':

                        if re.match(r'^(true)$', str(line), re.IGNORECASE):
                            result = 'true'
                        else:
                            result = 'false'

                    else:
                        result = line

                    print(f"result is  {result}", file=sys.stderr)
                    self.frames.set_value(self.operands[0].frame, self.operands[0].value, result, type2)

                if self.jumper.input_index < (len(self.input) - 1):
                    self.jumper.input_index += 1

                self.jumper.current += 1

            case 'WRITE':

                self.expected = ['symb']
                self.check_operands()

                value = self.get_op_val(0)
                type1 = self.get_op_type(0)

                print(f"{value}", file=sys.stderr)
                if value == 'nil':
                    print("", end='')
                else:
                    print(value, end='')

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
                    if (type1 == 'nil') or (type2 == 'nil'):
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
                    if (type1 == 'nil') or (type2 == 'nil'):
                        result = False
                    else:
                        result = int(value1) == int(value2)
                else:
                    result = value1 == value2

                if result:
                    self.jumper.current += 1
                else:
                    self.jumper.current = self.jumper.labels[label_name]

            case 'EXIT':
                self.expected = ['symb']
                self.check_operands()

                value1 = self.get_op_val(0)
                type1 = self.get_op_type(0)

                if type1 != 'int':
                    exit(53)

                if int(value1) < 0 or int(value1) > 49:
                    exit(57)

                sys.exit(int(value1))

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
    """helper class for interpret, it is in charge trnasformin xml to loist of instructions"""
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
        """creates xml tree structure"""
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
        """basick check of xml structure"""

        try:
            if self.root.attrib['language'].upper() != "IPPcode23".upper():  # name a description nekotroluju kdyz
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
        """creates a list of instructions for further processing in interpret"""
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

            instruction_list = sorted(instruction_list, key=lambda x: x.order, reverse=False)

        right_order = 0
        for j in instruction_list:
            j.order = right_order
            right_order += 1

        return instruction_list


class Jumper:
    """class is in charge of keeping the data about flow control"""
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
    """main class managing all the tasks in interpretatin"""
    def __init__(self, source_file, input_file):
        self.source = source_file
        self.input = input_file
        self.in_list = []
        self.in_cnt = 0
        self.frames = Frames()
        self.datastack = []
        self.labels = []

    def main(self):
        """managing the interpretation"""
        jumper = Jumper()
        xml = Read_source(self.source, self.frames, self.labels, self.datastack, self.in_list, jumper, self.input)
        xml.load()
        xml.check()
        self.in_list = xml.fill_list()

        jumper.extract_labels(self.in_list)

        while jumper.current < len(self.in_list):

            instruction = self.in_list[jumper.current]
            if instruction is None:
                break
            else:
                instruction.execute()


def replace_unicode_escape_sequences(s):
    """helper function for thansforming xml strings to it's real value"""
    pattern = r'\\[0-9]{3}'

    def replace_unicode(match):
        escape_sequence = match.group(0)
        unicode_char = chr(int(escape_sequence[2:], 10))
        return unicode_char

    result = re.sub(pattern, replace_unicode, s)
    return result

"""Starting of the program and loading arguments """

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
