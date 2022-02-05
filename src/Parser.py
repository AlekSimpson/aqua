import tokens as tk
from Types import Integer
from Error import InvalidSyntaxError
from Node import *
from ParseResult import ParseResult
from tokens import Token


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_idx = 0
        self.curr_token = self.tokens[self.token_idx]

    def advance(self):
        self.token_idx += 1
        if self.token_idx < len(self.tokens):
            self.curr_token = self.tokens[self.token_idx]

    def reverse(self, amount=1):
        self.token_idx -= amount
        self.update_current_token()
        return self.curr_token

    def update_current_token(self):
        if self.token_idx >= 0 and self.token_idx < len(self.tokens):
            self.curr_token = self.tokens[self.token_idx]

    def parse(self):  # returns Node, Error
        node_result, parse_result = self.statements()
        if parse_result.error is not None:
            if self.curr_token.type != tk.TT_EOF:
                return (None, parse_result.failure(parse_result.error))
            print(parse_result.error.as_string())
            return (None, parse_result.error)

        return (node_result, None)

    def call(self):
        res = ParseResult()
        atom, atom_res = self.atom()
        _ = res.register(atom_res)
        if res.error is not None:
            return (None, res)
        if self.curr_token.type_name == tk.TT_LPAREN:
            _ = res.register(self.advance())
            arg_nodes = []

            if self.curr_token.type_name == tk.TT_RPAREN:
                _ = res.register(self.advance())
            else:
                expr, expr_res = self.expr()
                if expr_res.error is not None:
                    return (None, expr_res)
                arg_nodes.append(res.register(expr))
                if expr_res.error is not None:
                    pos = expr.token.pos
                    err = InvalidSyntaxError(
                        "Expected closing parenthese in function declaration", pos
                    )
                    _ = res.failure(err)
                    return (None, res)

                while self.curr_token.type_name == tk.TT_COMMA:
                    _ = res.register(self.advance())

                    expr, expr_res = self.expr()
                    if expr_res.error is not None:
                        return (None, expr_res)
                    arg_nodes.append(res.register(expr))

                if self.curr_token.type_name != tk.TT_RPAREN:
                    pos = expr.token.pos
                    err = InvalidSyntaxError(
                        "Expected closing parenthese in function declaration", pos
                    )
                    _ = res.failure(err)
                    return (None, res)

                _ = res.register(self.advance())

            return (res.success(CallNode(atom, arg_nodes)), res)
        elif self.curr_token.type_name == tk.TT_LBRACKET:
            _ = res.register(self.advance())

            if self.curr_token.type_name != tk.TT_INT:
                pos = self.curr_token.pos
                err = InvalidSyntaxError("Array index must be an integer", pos)
                _ = res.failure(err)
                return (None, res)

            index, idx_err = self.atom()
            if idx_err.error is not None:
                return (None, idx_err)

            if self.curr_token.type_name != tk.TT_RBRACKET:
                pos = self.curr_token.pos
                err = InvalidSyntaxError(
                    "Array subscripts must have a closing bracket", pos
                )
                return (None, res)

            _ = res.register(self.advance())

            if self.curr_token.type_name == tk.TT_EQ:
                _ = res.register(self.advance())

                if (
                    not self.curr_token.type_name != tk.TT_INT
                    and not self.curr_token.type_name != tk.TT_STRING
                ):
                    pos = self.curr_token.pos
                    err = InvalidSyntaxError(
                        "Array can only hold value types of int or string", pos
                    )
                    return (None, res)

                new_val, val_res = self.atom()
                if val_res.error is not None:
                    return (None, val_res)

                _ = res.register(self.advance())

                return (res.success(ArraySetNode(atom, index, new_val)), res)
            return (res.success(ArrayGetNode(atom, index)), res)
        return (res.success(atom), res)

    def atom(self):
        res = ParseResult()
        tok = self.curr_token
        returnVal = (None, res)

        if tok.type_name == tk.TT_INT:
            val = NumberNode(self.curr_token)
            _ = res.register(self.advance())
            returnVal = (res.success(val), res)

        elif tok.type_name == tk.TT_ID:
            _ = res.register(self.advance())
            return (res.success(VarAccessNode(tok)), res)

        elif tok.type_name == tk.TT_STRING:
            _ = res.register(self.advance())
            return (res.success(StringNode(tok)), res)

        elif tok.type_name == "LPAREN":
            _ = res.register(self.advance())
            expr, err = self.expr()
            if expr is not None:
                _ = res.register(expr)
                if self.curr_token.type_name == "RPAREN":
                    _ = res.register(self.advance())
                    returnVal = (res.success(expr), res)
                else:
                    p = tok.pos
                    _ = res.failure(InvalidSyntaxError("Expected ')'", p))
            if err is not None:
                _ = res.register(err)
        elif tok.type_name == tk.TT_LBRACKET:
            list_expr = res.register(self.list_expr())
            if res.error is not None:
                return (None, res)
            return res.success(list_expr)
        elif tok.type_name == "IF":
            if_expr, expr_res = self.if_expr()
            _ = res.register(expr_res)
            if res.error is not None:
                _ = res.failure(res.error)
            else:
                returnVal = (if_expr, res)
        elif tok.type_name == "FOR":
            for_expr, expr_res = self.for_expr()
            _ = res.register(expr_res)
            if res.error is not None:
                _ = res.failure(res.error)
            else:
                returnVal = (for_expr, res)
        elif tok.type_name == "WHILE":
            while_expr, expr_res = self.while_expr()
            _ = res.register(expr_res)
            if res.error is not None:
                _ = res.failure(res.error)
            else:
                returnVal = (while_expr, res)
        elif tok.type_name == "FUNC":
            func_def, func_res = self.func_def()
            _ = res.register(func_res)
            if res.error is not None:
                _ = res.failure(res.error)
            else:
                returnVal = (func_def, res)
        else:
            p = tok.pos
            _ = res.failure(
                InvalidSyntaxError(
                    "Expected, int, float, identifier, '+', '-', or '('", p
                )
            )
        return returnVal

    def list_expr(self):
        res = ParseResult()
        element_nodes = []

        if self.curr_token.type_name != tk.TT_LBRACKET:
            return res.failure(
                InvalidSyntaxError("Expected '[' in list", self.curr_token.pos)
            )

        _ = res.register(self.advance())

        if self.curr_token.type_name == tk.TT_RBRACKET:
            _ = res.register(self.advance())
        else:
            expr, expr_res = self.expr()
            if expr_res.error is not None:
                return (None, expr_res)
            element_nodes.append(res.register(expr))
            if expr_res.error is not None:
                p = expr.token.pos
                err = InvalidSyntaxError(
                    "Expected closing bracket in list declaration", pos
                )
                _ = res.failure(err)
                return (None, res)

            while self.curr_token.type_name == tk.TT_COMMA:
                _ = res.register(self.advance())

                expr, expr_res = self.expr()
                if expr_res.error is not None:
                    return (None, expr_res)
                element_nodes.append(res.register(expr))

            if self.curr_token.type_name != tk.TT_RBRACKET:
                pos = expr.token.pos
                err = InvalidSyntaxError(
                    "Expected closing bracket in list declaration", pos
                )
                _ = res.failure(err)
                return (None, res)

            _ = res.register(self.advance())
        return (res.success(ListNode(element_nodes)), res)

    def func_def(self):
        res = ParseResult()

        if not (self.curr_token.type_name == "FUNC"):
            p = self.curr_token.pos
            _ = res.failure(
                InvalidSyntaxError(
                    "Expected 'method' keyword in function declaration", p
                )
            )
            return (None, res)

        _ = res.register(self.advance())

        name_token = Token()
        if self.curr_token.type_name == tk.TT_ID:
            name_token = self.curr_token
            _ = res.register(self.advance())

        if not (self.curr_token.type_name == tk.TT_LPAREN):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected '(' in function defintion", p))
            return (None, res)

        _ = res.register(self.advance())
        arg_name_tokens = []
        arg_type_tokens = []

        if self.curr_token.type_name == tk.TT_ID:
            look_for_args = True
            while look_for_args:
                if self.curr_token.type_name != tk.TT_ID:
                    pos = self.curr_token.pos
                    _ = res.failure(
                        InvalidSyntaxError(
                            "Expected identifier after comma in function definition",
                            pos,
                        )
                    )
                    return (None, res)
                arg_name_tokens.append(self.curr_token)
                res.register(self.advance())

                if self.curr_token.type_name != tk.TT_COLON:
                    pos = self.curr_token.pos
                    res.failure(
                        InvalidSyntaxError(
                            "Expected ':' in arguement type declaration in function {name_token.value}",
                            pos,
                        )
                    )
                    return (None, res)
                res.register(self.advance())

                if self.curr_token.type_dec is None:
                    pos = self.curr_token.pos
                    res.failure(
                        InvalidSyntaxError(
                            f"Expected arguement {arg_name_tokens[-1].value} to have a type declaration in function {name_token.value}",
                            pos,
                        )
                    )
                    return (None, res)
                arg_type_tokens.append(self.curr_token)
                res.register(self.advance())

                look_for_args = self.curr_token.type_name == tk.TT_COMMA
                if not look_for_args:
                    break
                res.register(self.advance())

            if not (self.curr_token.type_name == tk.TT_RPAREN):
                pos = self.curr_token.pos
                _ = res.failure(
                    InvalidSyntaxError("Expected ')' in function defintion", pos)
                )
                return (None, res)
        else:
            # BUG The check for RPAREN could probably just be moved into one check if statement instead of having one in an else
            if not (self.curr_token.type_name == tk.TT_RPAREN):
                pos = self.curr_token.pos
                _ = res.failure(
                    InvalidSyntaxError(
                        "Expected identifier or ')' in function definition", pos
                    )
                )
                return (None, res)

        _ = res.register(self.advance())

        if self.curr_token.type_name != tk.TT_COLON:
            pos = self.curr_token.pos
            res.failure(InvalidSyntaxError("Expected ':' in function declaration", pos))
            return (None, res)

        _ = res.register(self.advance())

        if self.curr_token.type_dec is None:
            pos = self.curr_token.pos
            res.failure(
                InvalidSyntaxError("Expected return type in function declaration", pos)
            )
            return (None, res)
        returnType = self.curr_token

        _ = res.register(self.advance())

        if self.curr_token.type_name == tk.TT_ARROW:
            _ = res.register(self.advance())

            node_to_return, return_res = self.expr()
            _ = res.register(return_res)
            if res.error is not None:
                return (None, res)

            return (
                res.success(
                    FuncDefNode(
                        node_to_return,
                        returnType,
                        name_token,
                        arg_name_tokens,
                        arg_type_tokens,
                        False,
                    )
                ),
                res,
            )

        if self.curr_token.type_name != "LCURLY":
            pos = self.curr_token.pos
            res.failure(InvalidSyntaxError("Expected '{'", pos))
            return (None, res)

        res.register(self.advance())

        if self.curr_token.type_name != tk.TT_NEWLINE:
            pos = self.curr_token.pos
            res.failure(InvalidSyntaxError("Expected '->' in function or '{'", pos))
            return (None, res)

        res.register(self.advance())

        body, body_res = self.statements()
        res.register(body_res)
        if res.error is not None:
            return (None, res)

        return_nil = True
        for node in body.element_nodes:
            if node.classType == 15:
                return_nil = False
                break

        if self.curr_token.type_name != "RCURLY":
            pos = self.curr_token.pos
            res.failure(InvalidSyntaxError("Expected '}'", pos))
            return (None, res)

        res.register(self.advance())
        returnVal = (
            res.success(
                FuncDefNode(
                    body,
                    returnType,
                    name_token,
                    arg_name_tokens,
                    arg_type_tokens,
                    return_nil,
                )
            ),
            res,
        )
        return returnVal

    def for_expr(self):
        res = ParseResult()

        if not (self.curr_token.type_name == "FOR"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected 'for'", p))
            return (None, res)

        _ = res.register(self.advance())

        if not (self.curr_token.type_name == "IDENTIFIER"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected variable", p))
            return (None, res)

        iterator_token = self.curr_token
        _ = res.register(self.advance())

        if not (self.curr_token.type_name == "IN"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected 'in' keyword", p))
            return (None, res)

        _ = res.register(self.advance())

        start_value, start_res = self.expr()
        _ = res.register(start_res)
        if res.error is not None:
            return (None, res)

        iterator_var = VarAssignNode(iterator_token, start_value, [1, Integer(64)])

        if not (self.curr_token.type_name == "COLON"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected ':' in range", p))
            return (None, res)

        _ = res.register(self.advance())

        end_value, end_res = self.expr()
        _ = res.register(end_res)
        if res.error is not None:
            return (None, res)

        if not (self.curr_token.type_name == "LCURLY"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected '{' in for loop", p))
            return (None, res)

        _ = res.register(self.advance())

        if self.curr_token.type_name == tk.TT_NEWLINE:
            res.register(self.advance())

            body, body_result = res.register(self.statements())
            if res.error is not None:
                return (None, res)

            if self.curr_token.type_name != "RCURLY":
                pos = self.curr_token.pos
                res.failure(InvalidSyntaxError("Expected '}'", pos))
                return (None, res)

            res.register(self.advance())

            return (
                res.success(ForNode(iterator_var, start_value, end_value, body, True)),
                res,
            )

        body, body_res = self.expr()
        _ = res.register(body_res)
        if res.error is not None:
            return (None, res)

        if not (self.curr_token.type_name == "RCURLY"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected '}' in for loop", p))
            return (None, res)

        return (
            res.success(ForNode(iterator_var, start_value, end_value, body, False)),
            res,
        )

    def while_expr(self):
        res = ParseResult()

        if not (self.curr_token.type_name == "WHILE"):
            p = self.curr_token.pos
            _ = res.failure(
                InvalidSyntaxError("Expected 'while' keyword in while loop", p)
            )
            return (None, res)

        _ = res.register(self.advance())

        cond_value, cond_res = self.expr()
        _ = res.register(cond_res)
        if res.error is not None:
            return (None, res)

        if not (self.curr_token.type_name == "LCURLY"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected '{' in while loop", p))
            return (None, res)

        _ = res.register(self.advance())

        if self.curr_token.type_name == tk.TT_NEWLINE:
            res.register(self.advance())

            body, _ = res.register(self.statements())
            if res.error is not None:
                return (None, res)

            if self.curr_token.type_name != "RCURLY":
                pos = self.curr_token.pos
                res.failure(InvalidSyntaxError("Expeected '}'", pos))
                return (None, res)

            res.register(self.advance())

            return (res.success(WhileNode(cond_value, body, True)), res)

        body_value, body_res = self.expr()
        _ = res.register(body_res)
        if res.error is not None:
            return (None, res)

        if not (self.curr_token.type_name == "RCURLY"):
            p = self.curr_token.pos
            _ = res.failure(InvalidSyntaxError("Expected '}' in while loop", p))
            return (None, res)

        return (res.success(WhileNode(cond_value, body_value, False)), res)

    def if_expr(self):
        res = ParseResult()
        all_cases, cases_res = self.if_expr_cases("IF")
        res.register(cases_res)
        if res.error is not None:
            return (None, res)
        cases, else_case = all_cases

        return (res.success(IfNode(cases, else_case)), res)

    def if_expr_cases(self, case_keyword):
        res = ParseResult()
        cases = []
        else_case = None

        if self.curr_token.type_name != case_keyword:
            pos = self.curr_token.pos
            res.failure(InvalidSyntaxError("Expected 'if'", pos))
            return (None, res)

        res.register(self.advance())

        condition, cond_result = self.expr()
        res.register(cond_result)
        if res.error is not None:
            return (None, res)

        if self.curr_token.type_name != "LCURLY":
            pos = self.curr_token.pos
            res.register(InvalidSyntaxError("Expected '{'", pos))
            return (None, res)

        res.register(self.advance())

        if self.curr_token.type_name == tk.TT_NEWLINE:
            res.register(self.advance())

            all_statements, statements_res = self.statements()
            res.register(statements_res)
            if res.error is not None:
                return (None, res)
            statements = all_statements
            cases.append([condition, statements, True])

            if self.curr_token.type_name != "RCURLY":
                pos = self.curr_token.pos
                res.register(InvalidSyntaxError("Expected '}'", pos))
                return (None, res)
            res.register(self.advance())

            all_cases, cases_res = self.if_expr_b_or_c()
            res.register(cases_res)
            if res.error is not None:
                return (None, res)
            new_cases, else_case = all_cases
            if len(new_cases) != 0:
                cases.extend(new_cases)
        else:
            expr, expr_res = self.expr()
            res.register(expr_res)
            if res.error is not None:
                return (None, res)
            cases.append([condition, expr, False])

            if self.curr_token.type_name != "RCURLY":
                pos = self.curr_token.pos
                res.register(InvalidSyntaxError("Expected '}'", pos))
                return (None, res)
            res.register(self.advance())

            all_cases, else_res = self.if_expr_b_or_c()
            res.register(else_res)
            if res.error is not None:
                return (None, res)
            new_cases, else_case = all_cases
            if len(new_cases) != 0:
                cases.extend(new_cases)

        res.success([cases, else_case])

        return ([cases, else_case], res)

    def if_expr_c(self):
        res = ParseResult()
        else_case = None

        if self.curr_token.type_name == "ELSE":
            res.register(self.advance())

            if self.curr_token.type_name != "LCURLY":
                pos = self.curr_token.pos
                res.register(InvalidSyntaxError("Expected '{' in else statement", pos))
                return (None, res)

            res.register(self.advance())

            if self.curr_token.type_name == tk.TT_NEWLINE:
                res.register(self.advance())

                statements, statements_res = self.statements()
                res.register(statements_res)
                if res.error is not None:
                    return res
                else_case = [statements, True]

                if self.curr_token.type_name == "RCURLY":
                    res.register(self.advance())
                else:
                    pos = self.curr_token.pos
                    res.failure(InvalidSyntaxError("Expected '}' in if statement", pos))
                    return (None, res)
            else:
                expr, expr_res = self.expr()
                res.register(expr_res)
                if res.error is not None:
                    return (None, res)

                else_case = [expr, False]
        res.success(else_case)

        return (else_case, res)

    def if_expr_b_or_c(self):
        res = ParseResult()
        cases = []
        else_case = None

        if self.curr_token.type_name == "ELIF":
            all_cases, cases_res = self.if_expr_b()
            res.register(cases_res)
            if res.error is not None:
                return (None, res)
            cases, else_case = all_cases
        else:
            else_case, else_res = self.if_expr_c()
            res.register(else_res)
            if res.error is not None:
                return (None, res)

        res.success([cases, else_case])

        return ([cases, else_case], res)

    def if_expr_b(self):
        return self.if_expr_cases("ELIF")

    def power(self):
        return self.bin_op(self.call, [tk.TT_POW], self.factor)

    def factor(self):
        res = ParseResult()
        tok = self.curr_token
        returnVal = (None, res)

        if tok.type_name == "PLUS" or tok.type_name == "MINUS":
            _ = res.register(self.advance())
            fac_node, fac_res = self.factor()

            if fac_node is not None:
                _ = res.register(self.factor())
                returnVal = (res.success(UnaryNode(tok, fac_node)), res)

            if fac_res.error is not None:
                _ = res.failure(fac_res.error)
                returnVal = (None, res)
        else:
            returnVal = self.power()

        return returnVal

    def term(self):
        return self.bin_op(self.factor, [tk.TT_MUL, tk.TT_DIV])

    def statements(self):
        res = ParseResult()
        statements = []

        while self.curr_token.type_name == tk.TT_NEWLINE:
            res.register(self.advance())

        statement, _ = res.register(self.statement())
        if res.error is not None:
            return res

        statements.append(statement)

        more_statements = True

        while True:
            newline_count = 0
            while self.curr_token.type_name == tk.TT_NEWLINE:
                res.register(self.advance())
                newline_count += 1
            if newline_count == 0:
                more_statements = False

            if not more_statements:
                break
            statement, _ = res.register(self.statement())
            if not statement:
                more_statements = False
                continue
            statements.append(statement)

        return_value = ListNode(statements)
        res.success(return_value)

        return (return_value, res)

    def statement(self):
        res = ParseResult()
        return_node = None

        if self.curr_token.type_name == "RETURN":
            res.register(self.advance())
            if self.curr_token.type_name != "NEWLINE":
                expr, expr_res = self.expr()
                if expr_res.error is not None:
                    return (None, expr_res)
                return_node = ReturnNode(expr)
            return (return_node, res)

        expr, expr_res = self.expr()
        if expr_res.error is not None:
            return (None, res)

        if expr_res.error is not None:
            return (None, res.failure(expr_res.error))

        return (expr, res)

    def expr(self):
        res = ParseResult()
        jump_back = self.token_idx

        if self.curr_token.type_name == tk.TT_ID:
            var_name = self.curr_token
            res.register(self.advance())

            if self.curr_token.type_name == tk.TT_COLON:
                res.register(self.advance())

                if self.curr_token.type_dec is None:
                    pos = self.curr_token.pos
                    res.register(
                        InvalidSyntaxError("Variable declaration must have a type", pos)
                    )
                    return (None, res)
                type_tok = self.curr_token
                res.register(self.advance())

                if self.curr_token.type_name == tk.TT_EQ:
                    _ = res.register(self.advance())

                    val, result = self.expr()
                    _ = res.register(result)

                    if res.error is not None:
                        return (None, res)
                    else:
                        return (
                            res.success(
                                VarAssignNode(var_name, val, type_tok.type_dec)
                            ),
                            res,
                        )
            if self.curr_token.type_name == tk.TT_EQ:
                _ = res.register(self.advance())

                val, result = self.expr()
                _ = res.register(result)

                if res.error is not None:
                    return (None, res)
                else:
                    return (res.success(VarUpdateNode(var_name, val)), res)

        self.token_idx = jump_back
        self.curr_token = self.tokens[self.token_idx]

        return self.bin_op(self.comp_expr, [tk.TT_AND, tk.TT_OR])

    def comp_expr(self):
        res = ParseResult()

        if self.curr_token.type_name == "NOT" or self.curr_token.type_name == "AND":
            op_tok = self.curr_token
            _ = res.register(self.advance())

            node, node_result = self.comp_expr()
            _ = res.register(node_result)
            if res.error is not None:
                return (None, res)

            return (UnaryOpNode(op_tok, node), res)

        node, node_result = self.bin_op(
            self.arith_expr,
            [tk.TT_EE, tk.TT_NE, tk.TT_LT, tk.TT_GT, tk.TT_LOE, tk.TT_GOE],
        )
        _ = res.register(node_result)
        if res.error is not None:
            _ = res.failure(res.error)
            return (None, res)
        return (node, res)

    def arith_expr(self):
        return self.bin_op(self.term, [tk.TT_PLUS, tk.TT_MINUS])

    def check_equal_to_ops(self, ops, type_name):
        for op in ops:
            if type_name == op:
                return True

        return False

    def bin_op(self, functionA, ops, functionB=None):
        res = ParseResult()

        func = functionB
        if functionB is None:
            func = functionA

        left, parse_result = functionA()
        _ = res.register(parse_result)
        if res.error is not None:
            return (None, res)

        loop_condition = self.check_equal_to_ops(ops, self.curr_token.type_name)
        while loop_condition:
            op_tok = VariableNode(self.curr_token)
            _ = res.register(self.advance())

            right, parse_result_ = func()
            _ = res.register(parse_result_)
            if res.error is not None:
                return (None, res)

            left = BinOpNode(left, op_tok, right)
            loop_condition = self.check_equal_to_ops(ops, self.curr_token.type_name)

        return (res.success(left), res)
