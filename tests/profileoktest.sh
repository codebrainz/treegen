#!/bin/bash

set -e

tests/genoktest.py > tests/ooooook.ast
python3 -m cProfile treegen -o misc/testcode.h tests/ooooook.ast > tests/profileok.txt
