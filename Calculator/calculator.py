from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import sympy as sp


@dataclass(frozen=True)
class CalculatorResult:
    """Container for symbolic results to mirror TI-89 style outputs."""

    input_expression: str
    result: object

    def as_float(self, precision: int = 10) -> float:
        """Return a numeric approximation of the result with configurable precision."""

        if precision <= 0:
            raise ValueError("Precision must be a positive integer")

        if not isinstance(self.result, sp.Basic):
            raise TypeError("Result is not a SymPy expression that can be evaluated")

        return float(sp.N(self.result, precision))


class TI89Calculator:
    """A lightweight TI-89 inspired calculator focused on algebra and calculus."""

    def __init__(self) -> None:
        self._allowed_functions = self._build_allowed_functions()

    def evaluate(
        self,
        expression: str,
        variables: Mapping[str, float | int | sp.Expr] | None = None,
    ) -> CalculatorResult:
        """Evaluate an expression with optional substitutions for symbols."""

        cleaned_variables = variables or {}
        expression_symbols = self._build_symbol_map(cleaned_variables.keys())
        parsed_expression = self._parse_expression(expression, expression_symbols)
        substituted = parsed_expression.subs(
            {expression_symbols[key]: value for key, value in cleaned_variables.items()}
        )
        simplified = sp.simplify(substituted)
        return CalculatorResult(expression, simplified)

    def simplify_expression(self, expression: str) -> CalculatorResult:
        """Simplify an algebraic expression."""

        parsed_expression = self._parse_expression(expression, {})
        return CalculatorResult(expression, sp.simplify(parsed_expression))

    def solve_equation(self, equation: str, variable: str) -> CalculatorResult:
        """Solve a single equation for a target variable."""

        target_symbol = sp.Symbol(variable)
        equation_object = self._parse_equation(equation, {variable: target_symbol})
        solutions = sp.solve(equation_object, target_symbol)
        return CalculatorResult(equation, sp.Tuple(*solutions))

    def solve_system(
        self, equations: Sequence[str], variables: Sequence[str]
    ) -> CalculatorResult:
        """Solve a system of equations for the provided variables."""

        symbol_map = self._build_symbol_map(variables)
        parsed_equations = [
            self._parse_equation(equation, symbol_map) for equation in equations
        ]
        solution_symbols = [symbol_map[variable] for variable in variables]
        solutions = sp.solve(parsed_equations, solution_symbols, dict=True)
        return CalculatorResult("; ".join(equations), tuple(solutions))

    def derivative(
        self, expression: str, variable: str, order: int = 1
    ) -> CalculatorResult:
        """Compute the symbolic derivative of an expression with respect to a variable."""

        if order <= 0:
            raise ValueError("Derivative order must be a positive integer")
        variable_symbol = sp.Symbol(variable)
        parsed_expression = self._parse_expression(
            expression, {variable: variable_symbol}
        )
        derivative_expression = sp.diff(parsed_expression, variable_symbol, order)
        return CalculatorResult(expression, sp.simplify(derivative_expression))

    def integral(
        self,
        expression: str,
        variable: str,
        lower: float | int | sp.Expr | None = None,
        upper: float | int | sp.Expr | None = None,
    ) -> CalculatorResult:
        """Compute definite or indefinite integrals."""

        variable_symbol = sp.Symbol(variable)
        parsed_expression = self._parse_expression(
            expression, {variable: variable_symbol}
        )
        if lower is None and upper is None:
            result = sp.integrate(parsed_expression, variable_symbol)
        elif lower is not None and upper is not None:
            result = sp.integrate(parsed_expression, (variable_symbol, lower, upper))
        else:
            raise ValueError("Both bounds must be provided for a definite integral")
        return CalculatorResult(expression, sp.simplify(result))

    def limit(
        self,
        expression: str,
        variable: str,
        value: float | int | sp.Expr,
        direction: str = "two-sided",
    ) -> CalculatorResult:
        """Evaluate one-sided or two-sided limits."""

        direction_token = self._normalize_limit_direction(direction)
        variable_symbol = sp.Symbol(variable)
        parsed_expression = self._parse_expression(
            expression, {variable: variable_symbol}
        )
        result = sp.limit(
            parsed_expression, variable_symbol, value, dir=direction_token
        )
        return CalculatorResult(expression, result)

    def taylor_series(
        self, expression: str, variable: str, around: float | int | sp.Expr, order: int
    ) -> CalculatorResult:
        """Return the truncated Taylor series expansion up to the specified order."""

        if order <= 0:
            raise ValueError("Series order must be a positive integer")
        variable_symbol = sp.Symbol(variable)
        parsed_expression = self._parse_expression(
            expression, {variable: variable_symbol}
        )
        series_expansion = sp.series(
            parsed_expression, variable_symbol, around, order + 1
        )
        truncated = sp.simplify(series_expansion.removeO())
        return CalculatorResult(expression, truncated)

    def solve_differential_equation(
        self, equation: str, function: str
    ) -> CalculatorResult:
        """Solve an ordinary differential equation for the specified function."""

        function_symbol = sp.Function(function)
        independent_variable = sp.Symbol("x")
        parsed_equation = sp.sympify(
            equation,
            locals={
                **self._allowed_functions,
                function: function_symbol,
                "x": independent_variable,
            },
            convert_xor=True,
        )
        solution = sp.dsolve(sp.Eq(parsed_equation, 0))
        return CalculatorResult(equation, solution)

    def _parse_expression(
        self, expression: str, symbols: Mapping[str, sp.Symbol | sp.Expr]
    ) -> sp.Expr:
        return sp.sympify(
            expression, locals={**self._allowed_functions, **symbols}, convert_xor=True
        )

    def _parse_equation(
        self, equation: str, symbols: Mapping[str, sp.Symbol | sp.Expr]
    ) -> sp.Eq:
        if "=" in equation:
            lhs, rhs = equation.split("=", maxsplit=1)
        else:
            lhs, rhs = equation, "0"
        lhs_expr = self._parse_expression(lhs, symbols)
        rhs_expr = self._parse_expression(rhs, symbols)
        return sp.Eq(lhs_expr, rhs_expr)

    def _build_symbol_map(self, variables: Iterable[str]) -> Mapping[str, sp.Symbol]:
        return {name: sp.Symbol(name) for name in variables}

    def _normalize_limit_direction(self, direction: str) -> str:
        direction_map = {"two-sided": "+-", "left": "-", "right": "+"}
        if direction not in direction_map:
            raise ValueError("Direction must be 'two-sided', 'left', or 'right'")
        return direction_map[direction]

    def _build_allowed_functions(self) -> Mapping[str, object]:
        return {
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "asin": sp.asin,
            "acos": sp.acos,
            "atan": sp.atan,
            "sinh": sp.sinh,
            "cosh": sp.cosh,
            "tanh": sp.tanh,
            "exp": sp.exp,
            "log": sp.log,
            "ln": sp.log,
            "sqrt": sp.sqrt,
            "abs": sp.Abs,
            "pi": sp.pi,
            "E": sp.E,
            "e": sp.E,
        }
