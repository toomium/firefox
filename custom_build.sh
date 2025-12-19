#!/bin/bash

rm -r obj-x86_64-pc-linux-gnu

./mach clobber && ./mach build && ./mach package
