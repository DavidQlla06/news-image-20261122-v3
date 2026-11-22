#!/usr/bin/env python3
"""Entry point for the make.fun grader (Python 3.13, standard library only).

Copies the committed entry.png (drawn by generate.py) to the output
directory: $MAKEFUN_OUTPUT_DIR if set, otherwise /output.
"""

import os
import shutil
import sys


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)
    print("copied", src, "->", dst, os.path.getsize(dst), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
