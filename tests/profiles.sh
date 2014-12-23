#!/bin/bash

set -e

echo "Running all test profiles..."

tests/profileoktest.sh
tests/profilebigtest.sh

echo "Have a look at the \`tests/profileok.txt' and \`tests/profilebig.txt' files"
