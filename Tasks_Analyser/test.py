import re

line = "2025-05-11 17:06:38,732 - mmu1 - ANALYSE - START wait for maestro to complete undocking (3,) (workers_conrtoller.py:156)"

# Extract any parameter list in the first parentheses
match = re.search(r"\(([^()]+)\)", line)
if match:
    param_str = match.group(1)  # e.g., "1200, 2500, 90"
    params = [int(x.strip()) for x in param_str.split(',') if x.strip().isdigit()]
    print(params)  # Output: [1200, 2500, 90]