"""An example script to test subprocess."""

import sys
import time

print("Stdout line 1")
print("Stdout line 2")
if "stderr" in sys.argv:
    print("Stderr line 1", file=sys.stderr)

if "wait" in sys.argv:
    time.sleep(0.5)

if "non-zero" in sys.argv:
    sys.exit(1)

if "input" in sys.argv:
    user_input = input("Provide an input: ")
    print("Provided:", user_input)
