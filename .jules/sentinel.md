## 2025-11-30 - [Input Length Validation in SymPy Calculator]
**Vulnerability:** Unbounded input length in a calculator app using `sympy.parse_expr` allows potential DoS via resource exhaustion (CPU/Memory).
**Learning:** Even with restricted globals in `eval`-based parsers, the parsing process itself (or subsequent evaluation of huge expressions) can be a DoS vector.
**Prevention:** Enforce strict length limits on all user-supplied strings before passing them to expensive parsing logic.
