#!/usr/bin/env python3
"""
Простой компилятор для языка арифметических выражений.
Поддерживает: числа, сложение, вычитание, умножение, деление, скобки.
Пример: (2 + 3) * 4 - 10 / 2
"""

from dataclasses import dataclass
from typing import List, Union, Optional
from enum import Enum, auto


# ==================== ЛЕКСЕР ====================

class TokenType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MUL = auto()
    DIV = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: Union[int, str]


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
    
    def peek(self) -> Optional[str]:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None
    
    def advance(self) -> Optional[str]:
        char = self.peek()
        self.pos += 1
        return char
    
    def skip_whitespace(self):
        while self.peek() and self.peek().isspace():
            self.advance()
    
    def number(self) -> Token:
        start = self.pos
        while self.peek() and self.peek().isdigit():
            self.advance()
        value = int(self.source[start:self.pos])
        return Token(TokenType.NUMBER, value)
    
    def next_token(self) -> Token:
        self.skip_whitespace()
        
        char = self.peek()
        if char is None:
            return Token(TokenType.EOF, "")
        
        if char.isdigit():
            return self.number()
        
        self.advance()
        if char == '+':
            return Token(TokenType.PLUS, '+')
        elif char == '-':
            return Token(TokenType.MINUS, '-')
        elif char == '*':
            return Token(TokenType.MUL, '*')
        elif char == '/':
            return Token(TokenType.DIV, '/')
        elif char == '(':
            return Token(TokenType.LPAREN, '(')
        elif char == ')':
            return Token(TokenType.RPAREN, ')')
        
        raise LexerError(f"Неизвестный символ: {char}")
    
    def tokenize(self) -> List[Token]:
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


# ==================== AST ====================

@dataclass
class NumberNode:
    value: int


@dataclass
class BinaryOpNode:
    left: 'ASTNode'
    op: TokenType
    right: 'ASTNode'


ASTNode = Union[NumberNode, BinaryOpNode]


# ==================== ПАРСЕР ====================

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current(self) -> Token:
        return self.tokens[self.pos]
    
    def consume(self, expected: TokenType) -> Token:
        token = self.current()
        if token.type != expected:
            raise ParseError(f"Ожидался токен {expected}, получен {token.type}")
        self.pos += 1
        return token
    
    def parse(self) -> ASTNode:
        node = self.expression()
        if self.current().type != TokenType.EOF:
            raise ParseError("Ожидался конец выражения")
        return node
    
    def expression(self) -> ASTNode:
        """expression := term (('+' | '-') term)*"""
        node = self.term()
        
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current().type
            self.pos += 1
            right = self.term()
            node = BinaryOpNode(node, op, right)
        
        return node
    
    def term(self) -> ASTNode:
        """term := factor (('*' | '/') factor)*"""
        node = self.factor()
        
        while self.current().type in (TokenType.MUL, TokenType.DIV):
            op = self.current().type
            self.pos += 1
            right = self.factor()
            node = BinaryOpNode(node, op, right)
        
        return node
    
    def factor(self) -> ASTNode:
        """factor := NUMBER | '(' expression ')'"""
        token = self.current()
        
        if token.type == TokenType.NUMBER:
            self.pos += 1
            return NumberNode(token.value)
        
        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            node = self.expression()
            self.consume(TokenType.RPAREN)
            return node
        
        raise ParseError(f"Неожиданный токен: {token.type}")


# ==================== ГЕНЕРАТОР КОДА ====================

class CodeGenerator:
    def __init__(self):
        self.instructions: List[str] = []
        self.temp_counter = 0
    
    def new_temp(self) -> str:
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def generate(self, node: ASTNode) -> str:
        """Генерирует код в стиле трех адресов"""
        result = self.emit(node)
        
        # Добавляем результат в аккумулятор
        self.instructions.append(f"ACC = {result}")
        
        return "\n".join(self.instructions)
    
    def emit(self, node: ASTNode) -> str:
        if isinstance(node, NumberNode):
            return str(node.value)
        
        if isinstance(node, BinaryOpNode):
            left = self.emit(node.left)
            right = self.emit(node.right)
            
            temp = self.new_temp()
            op_map = {
                TokenType.PLUS: '+',
                TokenType.MINUS: '-',
                TokenType.MUL: '*',
                TokenType.DIV: '/'
            }
            op = op_map[node.op]
            
            self.instructions.append(f"{temp} = {left} {op} {right}")
            return temp
        
        raise ValueError(f"Неизвестный узел: {node}")


# ==================== ИНТЕРПРЕТАТОР ====================

class Interpreter:
    def __init__(self):
        self.variables = {}
    
    def interpret(self, code: str) -> int:
        """Выполняет сгенерированный код"""
        lines = code.strip().split('\n')
        acc = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if '=' in line:
                parts = line.split('=')
                dest = parts[0].strip()
                expr = parts[1].strip()
                
                # Простое вычисление выражения
                result = eval(expr, {}, self.variables)
                
                if dest == 'ACC':
                    acc = result
                else:
                    self.variables[dest] = result
        
        return acc


# ==================== КОМПИЛЯТОР ====================

class Compiler:
    def compile(self, source: str) -> str:
        """Компилирует исходный код в промежуточное представление"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        generator = CodeGenerator()
        code = generator.generate(ast)
        
        return code
    
    def compile_and_run(self, source: str) -> int:
        """Компилирует и сразу выполняет код"""
        code = self.compile(source)
        interpreter = Interpreter()
        return interpreter.interpret(code)


# ==================== MAIN ====================

def main():
    compiler = Compiler()
    
    print("=" * 50)
    print("ПРОСТОЙ КОМПИЛЯТОР АРИФМЕТИЧЕСКИХ ВЫРАЖЕНИЙ")
    print("=" * 50)
    
    test_cases = [
        "2 + 3",
        "10 - 4",
        "3 * 4",
        "20 / 4",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10 / 2 + 3",
        "(10 - 2) * (3 + 1)",
        "((2 + 3) * 4 - 10) / 2",
    ]
    
    for expr in test_cases:
        print(f"\nВыражение: {expr}")
        try:
            code = compiler.compile(expr)
            print("Сгенерированный код:")
            for line in code.split('\n'):
                print(f"  {line}")
            
            result = compiler.compile_and_run(expr)
            print(f"Результат: {result}")
            
            # Проверка через Python
            expected = eval(expr)
            status = "✓" if result == expected else "✗"
            print(f"Ожидается: {expected} {status}")
        except Exception as e:
            print(f"Ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("Интерактивный режим (введите 'quit' для выхода)")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ('quit', 'exit', 'q'):
                break
            
            if not user_input:
                continue
            
            code = compiler.compile(user_input)
            print("Код:")
            for line in code.split('\n'):
                print(f"  {line}")
            
            result = compiler.compile_and_run(user_input)
            print(f"Результат: {result}")
        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
