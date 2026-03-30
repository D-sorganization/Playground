import os
import re

for r, d, f in os.walk("."):
    if ".git" in r or "venv" in r or ".venv" in r or "node_modules" in r:
        continue
    for file in f:
        if file.endswith(".py"):
            path = os.path.join(r, file)
            try:
                with open(path, encoding="utf-8") as file_obj:
                    content = file_obj.read()
            except UnicodeDecodeError:
                continue

            if not re.search(r"\bprint\(", content):
                continue

            # simple replacement
            content = re.sub(r"\bprint\(", "logger.info(", content)

            if "import logging" not in content:
                lines = content.split("\n")
                last_import_idx = -1
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        last_import_idx = i

                # if there is a docstring at top
                if last_import_idx == -1:
                    last_import_idx = 0

                lines.insert(last_import_idx + 1, "import logging")
                lines.insert(
                    last_import_idx + 2, "logger = logging.getLogger(__name__)"
                )
                content = "\n".join(lines)

            with open(path, "w", encoding="utf-8") as file_obj:
                file_obj.write(content)
