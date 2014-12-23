#!/bin/bash

set -e

tests/genbigtest.py > tests/eeeek.ast
python3 -m cProfile -s time treegen -o misc/testcode.h tests/eeeek.ast > tests/profilebig.txt
