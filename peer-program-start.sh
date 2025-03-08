#!/bin/bash
initial_directory = "$PWD"

make
mv peer peer-directory
./p2_registry 127.0.0.1 5468
cd peer-directory
./peer 127.0.0.1 5468 18
cd initial_directory