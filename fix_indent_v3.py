import sys

with open("sendgrid_handler.py", "r") as f:
    lines = f.readlines()

new_lines = []
current_indent = 4
for i, line in enumerate(lines):
    line_num = i + 1
    if line_num >= 331:
        stripped = line.strip()
        if not stripped:
            new_lines.append("\n")
            continue
        
        if stripped.startswith("def "):
            new_lines.append("    " + stripped + "\n")
        elif stripped.startswith("if ") or stripped.startswith("for ") or stripped.startswith("with "):
            new_lines.append("        " + stripped + "\n")
        elif stripped.startswith("return ") or "=" in stripped or "(" in stripped:
            # This is naive but let's try to handle the level after "if"
            # Previous line check
            prev_stripped = lines[i-1].strip() if i > 0 else ""
            if prev_stripped.endswith(":") and "def" not in prev_stripped:
                new_lines.append("            " + stripped + "\n")
            else:
                new_lines.append("        " + stripped + "\n")
        else:
            new_lines.append("        " + stripped + "\n")
    else:
        new_lines.append(line)

with open("sendgrid_handler.py", "w") as f:
    f.writelines(new_lines)
