#!/usr/bin/env python3
"""Fix remaining ruff errors in Project_GROOT."""
import re
from pathlib import Path


def fix_long_lines():
    """Fix E501 long line errors manually."""
    fixes = [
        # imitation_train.py line 89
        {
            "file": "Project_GROOT/train/imitation_train.py",
            "line_num": 89,
            "old": r'        state = np\.concatenate\(\[q, qdot, time_steps\[:, None\]\], axis=1\)  # \(T, num_dofs\*2 \+ 1\)',
            "new": "        # (T, num_dofs*2 + 1)\n        state = np.concatenate([q, qdot, time_steps[:, None]], axis=1)",
        },
        # imitation_train.py line 284
        {
            "file": "Project_GROOT/train/imitation_train.py",
            "line_num": 284,
            "old": r'            print\(f"Epoch {epoch}/{num_epochs}: loss={metrics\[\'loss\'\]:.6f}, lr={metrics\[\'lr\'\]:.6f}"\)',
            "new": '            print(\n                f"Epoch {epoch}/{num_epochs}: loss={metrics[\'loss\']:.6f}, "\n                f"lr={metrics[\'lr\']:.6f}"\n            )',
        },
    ]
    
    for fix in fixes:
        filepath = Path(fix["file"])
        if not filepath.exists():
            print(f"Skipping {filepath} - doesn't exist")
            continue
            
        content = filepath.read_text(encoding="utf-8")
        original = content
        
        # Try direct replacement first
        if fix["old"] in content:
            content = content.replace(fix["old"], fix["new"])
        else:
            # Try regex
            pattern = re.compile(fix["old"], re.MULTILINE)
            content = pattern.sub(fix["new"], content)
        
        if content != original:
            filepath.write_text(content, encoding="utf-8")
            print(f"✓ Fixed {filepath}")
        else:
            print(f"⚠ Could not find pattern in {filepath}")


if __name__ == "__main__":
    fix_long_lines()
    print("\nDone! Run 'ruff check Project_GROOT' to verify.")
