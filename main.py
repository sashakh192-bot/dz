import sys
import re
import argparse
import xml.etree.ElementTree as ET

# ----------------- Лексика -----------------

TOKEN_REGEX = re.compile(r"""
    (?:
    (?P<NUMBER>-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?) |
    (?P<ASSIGN>:=) |
    (?P<FUNC>abs|min) |
    (?P<NAME>[a-z]+) |
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<LBRACK>\[) |
    (?P<RBRACK>\]) |
    (?P<COLON>:) |
    (?P<COMMA>,) |
    (?P<SEMICOLON>;) |
    (?P<OP>[+\-])
    )
""", re.VERBOSE)



class Token:
    def __init__(self, typ, val):
        self.type = typ
        self.value = val

def tokenize(text):
    pos = 0
    tokens = []
    length = len(text)

    while pos < length:
        # пропускаем пробелы и переводы строк
        if text[pos].isspace():
            pos += 1
            continue

        m = TOKEN_REGEX.match(text, pos)
        if not m:
            raise SyntaxError(f"Синтаксическая ошибка около: {text[pos:pos+20]}")
        pos = m.end()

        for k, v in m.groupdict().items():
            if v:
                tokens.append(Token(k, v))
                break

    return tokens


# ----------------- Парсер -----------------

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.env = {}

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, typ):
        tok = self.peek()
        if not tok or tok.type != typ:
            raise SyntaxError(f"Ожидался {typ}")
        self.pos += 1
        return tok

    def parse(self):
        while self.peek():
            self.parse_assignment()
        return self.env

    def parse_assignment(self):
        name = self.consume("NAME").value
        self.consume("ASSIGN")
        value = self.parse_value()
        self.consume("SEMICOLON")
        self.env[name] = value

    def parse_value(self):
        tok = self.peek()

        if tok.type == "NUMBER":
            self.pos += 1
            return float(tok.value)

        if tok.type == "NAME":
            self.pos += 1
            if tok.value not in self.env:
                raise NameError(f"Неизвестная константа {tok.value}")
            return self.env[tok.value]

        if tok.type == "LPAREN":
            # смотрим следующий токен
            if self.tokens[self.pos + 1].type == "LBRACK":
                return self.parse_dict()
            else:
                return self.parse_expr()

        raise SyntaxError("Некорректное значение")

    def parse_dict(self):
        self.consume("LPAREN")
        self.consume("LBRACK")
        d = {}

        while self.peek().type != "RBRACK":
            key = self.consume("NAME").value
            self.consume("COLON")
            val = self.parse_value()
            d[key] = val
            if self.peek().type == "COMMA":
                self.consume("COMMA")

        self.consume("RBRACK")
        self.consume("RPAREN")
        return d

    def parse_expr(self):
        self.consume("LPAREN")

        tok = self.peek()
        if tok.type == "OP":
            op = self.consume("OP").value
        elif tok.type == "FUNC":
            op = self.consume("FUNC").value
        else:
            raise SyntaxError("Ожидался оператор или функция")

        args = []
        while self.peek().type != "RPAREN":
            args.append(self.parse_value())

        self.consume("RPAREN")
        return self.eval_expr(op, args)

    def eval_expr(self, op, args):
        if op == "+":
            return sum(args)
        if op == "-":
            return args[0] - sum(args[1:])
        if op == "abs":
            return abs(args[0])
        if op == "min":
            return min(args)
        raise SyntaxError(f"Неизвестная операция {op}")


# ----------------- XML -----------------

def to_xml(data):
    root = ET.Element("config")
    for k, v in data.items():
        root.append(value_to_xml(k, v))
    return root

def value_to_xml(name, val):
    elem = ET.Element("entry", name=name)
    if isinstance(val, dict):
        elem.set("type", "dict")
        for k, v in val.items():
            elem.append(value_to_xml(k, v))
    else:
        elem.set("type", "number")
        elem.text = str(val)
    return elem

# ----------------- main -----------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    text = sys.stdin.read()
    tokens = tokenize(text)
    ast = Parser(tokens).parse()

    root = to_xml(ast)
    tree = ET.ElementTree(root)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    main()
