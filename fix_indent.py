import sys

with open("sendgrid_handler.py", "r") as f:
    lines = f.readlines()

new_lines = []
# Assuming line 331 starts the _normalize_email method which was under-indented
for i, line in enumerate(lines):
    line_num = i + 1
    if line_num >= 331:
        if line.startswith("  def "):
            new_lines.append("    " + line[2:])
        elif line.startswith("    ") and not line.startswith("      "):
             # If it was indented 4 spaces, make it 8
             new_lines.append("    " + line)
        elif line.startswith("      "):
             # If it was indented 6 spaces, make it 8
             new_lines.append("  " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open("sendgrid_handler.py", "w") as f:
    f.writelines(new_lines)
