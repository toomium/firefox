from re import findall, search, MULTILINE
from os import path, makedirs
from glob import glob
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser(description='Generate C++ mutator factory from proto files')
    parser.add_argument('-d', '--dir', type=str, required=True)
    parser.add_argument('-o', '--output-file', type=str, default='moz.build')
    return parser.parse_args()



def gen_moz_build(outfile, cpps, headers):
    with open(outfile, 'w') as f:
        f.write("""# -*- Mode: python; c-basic-offset: 4; indent-tabs-mode: nil; tab-width: 40 -*-
# vim: set filetype=python:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# AUTO-GENERATED - DO NOT EDIT !!!!!!!!!!

Library("fuzzer-ipc-protocol-protobuf")

SOURCES += [""")
        for cpp in cpps:
            f.write("""
    "%s",""" % cpp)
        f.write("""
]

EXPORTS.mozilla.fuzzing.protobuf += [""")
        for header in headers:
            f.write("""
    "%s",""" % header)
        f.write("""
]

FINAL_LIBRARY = "xul"

""")

def main():
    #parse arguments
    args = parse_args()

    # check paths
    if not path.exists(args.dir):
        print(f"Input directory '{args.dir}' doesn't exist")
        return
    if not path.exists(args.output_file):
        makedirs(args.output_file)

    # find .ph.h and .pb.cc files in input dir
    cpps_paths = glob(path.join(args.dir, "**/*.pb.cc"), recursive=True)
    headers_paths = glob(path.join(args.dir, "**/*.pb.h"), recursive=True)
    cpps = sorted([path.basename(p) for p in cpps_paths], key=str.lower)
    headers = sorted([path.basename(p) for p in headers_paths], key=str.lower)

    if not cpps:
        print(f"No source files found in input directory")
        return

    outfile = path.join(args.dir, args.output_file)

    # parse all protocol + message names
    gen_moz_build(outfile, cpps, headers)

    print("\nDone!")
    print(f"Generated: {outfile}")
    print(f"Added {len(cpps)} source files and {len(headers)} header files")

if __name__ == "__main__":
    main()
