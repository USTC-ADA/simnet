#!/usr/bin/env python
import sys
import os
import argparse
import numpy as np
from qq_format import *
#from pk_format import *

parser = argparse.ArgumentParser(description="Make Q memmap dataset")
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--end', type=int, default=0)
parser.add_argument('--total-rows', type=int, default=0)
parser.add_argument('--cols', type=int, default=context_length*inst_length)
parser.add_argument('--stats', default="")
parser.add_argument('fname', nargs='*')
args = parser.parse_args()

start = args.start
end = args.end
output = args.fname[0]
if len(args.fname) > 1:
    output = os.path.join(os.path.dirname(args.fname[0]), "totalall")
output += ".mmap"
r = args.total_rows
w = context_length*inst_length
shp = (r, w)

print("Make Q dataset ", output, ", start from", start, ", end with", end, ", shape is ", shp, flush=True)

nlines = 0
nfilled = 0
file_idx = 0
bad_lines = 0
bad_content = 0
#all_feats = np.memmap(output, dtype=np.float32, mode='w+', shape=shp)
all_feats = np.memmap(output, dtype=np.uint16, mode='w+', shape=shp)
tmp_data = np.arange(w, dtype=np.uint16)

if args.stats != "":
    print('Load stats file %s.' % args.stats)
    fs = np.load(args.stats)
    all_var = fs['all_var']
    all_fac = np.sqrt(all_var)

for i in range(len(args.fname)):
    fname = args.fname[i]
    print("read", fname, flush=True)
    with open(fname) as f:
        for line in f:
            if nfilled >= r:
                print("Find more lines than the input shape.")
                break
            if nlines < start:
                nlines += 1
                continue

            try:
                vals = [int(s) for s in line.rstrip().split(' ')]
            except:
                bad_lines += 1
                print("Bad line", flush=True)
                continue
            #print(vals)

            try:
                assert len(vals) % inst_length == 0
                assert len(vals) <= w
                tmp_data[0:len(vals)] = np.array(vals)
                tmp_data[len(vals):w] = 0
                all_feats[nfilled] = tmp_data
                #all_feats[nfilled, 0:len(vals)] = np.array(vals)
                #all_feats[nfilled, len(vals):w] = 0
                if args.stats != "":
                    inst_num = int(len(vals) / inst_length)
                    for j in range(inst_num):
                        all_feats[nfilled, inst_length*j:inst_length*(j+1)] /= all_fac
            except:
                print("Bad content:", len(vals), vals, flush=True)
                bad_content += 1
                continue

            if nfilled == 0:
                print("First sample:", all_feats[nfilled].shape, len(vals))
                print(all_feats[nfilled], flush=True)
            nfilled += 1
            nlines += 1
            if end != 0 and nlines == end:
                break

            if nfilled % 5000000 == 0:
                all_feats.flush()
                print("Have filed %d" % nfilled, flush=True)

all_feats.flush()
print("Finished with ", nfilled, "entries, ", nlines, "lines, ", bad_lines, "bad lines", bad_content, "bad contents.")
