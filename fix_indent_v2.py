import sys

with open("sendgrid_handler.py", "r") as f:
    lines = f.readlines()

new_lines = []
# From line 331 onwards, we need to fix the methods in the SendgridHandler class.
# They should have 4 spaces for 'def' and 8 spaces for the body.
current_method = None
for i, line in enumerate(lines):
    line_num = i + 1
    if line_num >= 331:
        stripped = line.strip()
        if not stripped:
            new_lines.append("\n")
            continue
        
        if stripped.startswith("def "):
            new_lines.append("    " + stripped + "\n")
        else:
            new_lines.append("        " + stripped + "\n")
    else:
        new_lines.append(line)

with open("sendgrid_handler.py", "w") as f:
    f.writelines(new_lines)
