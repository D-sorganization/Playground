import sympy as sp

from ti89.calculator import TI89Calculator


def test_evaluate_with_trigonometric_identity() -> None:
    calculator = TI89Calculator()
    result = calculator.evaluate("sin(x)^2 + cos(x)^2", {"x": sp.pi / 4})
    assert sp.simplify(result.result - 1) == 0


def test_solve_quadratic_equation() -> None:
    calculator = TI89Calculator()
    solutions = calculator.solve_equation("x^2 - 5*x + 6 = 0", "x").result
    assert {sp.Integer(2), sp.Integer(3)} == set(solutions)


def test_solve_linear_system() -> None:
    calculator = TI89Calculator()
    solution = calculator.solve_system(["x + y = 5", "x - y = 1"], ["x", "y"]).result[0]
    assert solution == {sp.Symbol("x"): 3, sp.Symbol("y"): 2}


def test_symbolic_derivative_and_integral() -> None:
    calculator = TI89Calculator()
    derivative = calculator.derivative("sin(x) * exp(x)", "x").result
    assert (
        sp.simplify(
            derivative
            - sp.exp(sp.Symbol("x")) * (sp.sin(sp.Symbol("x")) + sp.cos(sp.Symbol("x")))
        )
        == 0
    )

    integral = calculator.integral("exp(-x)", "x").result
    assert sp.simplify(integral + sp.exp(-sp.Symbol("x"))) == 0


def test_definite_integral_and_limit() -> None:
    calculator = TI89Calculator()
    integral = calculator.integral("x", "x", 0, 3).result
    assert integral == sp.Rational(9, 2)

    limit_result = calculator.limit("sin(x)/x", "x", 0, direction="right").result
    assert limit_result == 1


def test_taylor_series_and_differential_equation_solution() -> None:
    calculator = TI89Calculator()
    taylor = calculator.taylor_series("sin(x)", "x", 0, order=5).result
    assert (
        taylor == sp.Symbol("x") - sp.Symbol("x") ** 3 / 6 + sp.Symbol("x") ** 5 / 120
    )

    ode_solution = calculator.solve_differential_equation(
        "Derivative(f(x), x) + f(x)", "f"
    ).result
    assert (
        sp.simplify(ode_solution.rhs - sp.exp(-sp.Symbol("x")) * sp.Symbol("C1")) == 0
    )
