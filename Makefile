# Group Members: Vincent Roberson and Muhammad I Sohail
# ECEE 446 Section 1
# Spring 2025
EXE = peer
CFLAGS = -Wall
CXXFLAGS = -Wall
LDLIBS =
CC = gcc
CXX = g++

.PHONY: all
all: $(EXE)

# Implicit rules defined by Make, but you can redefine if needed
#
#peer: peer.c
#	$(CC) $(CFLAGS) peer.c $(LDLIBS) -o peer
#
# OR
#
#peer: peer.cc
#	$(CXX) $(CXXFLAGS) peer.cc $(LDLIBS) -o peer

.PHONY: clean
clean:
	rm -f $(EXE)