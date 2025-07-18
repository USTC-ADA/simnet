#!/usr/bin/env python

import sys
import argparse
import numpy as np
from input_format import *

context_length = 94
iter_num = 1024 * 16 * 32 * 16
inst_length = 39

def make_feature_from_context(vals): # Vals is all instructions concatenated.
    feat = []
    instrs = split_instr(vals)
    inst_num = len(instrs)
    assert inst_num <= context_length
    for i in range(context_length):
        if i < inst_num:
            #print(instrs[i])
            feat_from_instr = make_feature_from_instr(instrs[i])
            #print('feat_from_instr len is' , len(feat_from_instr))
            #print(feat_from_instr)
            assert len(feat_from_instr) == inst_length
            feat += feat_from_instr
        else:
            feat += zeros(inst_length)
    return feat, inst_num # inst_length*context_length


parser = argparse.ArgumentParser(description="Make ML dataset")
parser.add_argument('--num', type=int, nargs=1, default=0)
parser.add_argument('--start', type=int, nargs=1, default=0)
parser.add_argument('--output-base', type=str)
parser.add_argument('fname', nargs='*')
args = parser.parse_args()

fname = args.fname[0]
num = args.num
start = args.start
print("Make ML dataset for", fname, "with", num, "instructions, start from", start)

nlines = 1
bad_lines = 0
bad_content = 0

all_feats = []
idx = 0
with open(fname) as f:
    for line in f:
        if nlines <= start:
            nlines = nlines + 1
            continue

        try:
            vals = [int(s) for s in line.rstrip().split(' ')]
        except:
            bad_lines += 1
            continue
        #print(vals)
        try:
            feat, length = make_feature_from_context(vals)
        except:
            bad_content += 1
            print(vals)
            print(bad_content, bad_lines)
            continue
        #print('feat_from_cxt len is' , len(feat))
        #print(feat)
        all_feats.append(feat)
        if nlines == 1:
            print(feat)

        if num != 0:
            if nlines == num:
                nlines = nlines + 1
                break

        if ((nlines % iter_num) == 0):
            print("So far have %d" % nlines)
            x = np.array(all_feats)
            idx = int(nlines / iter_num) - 1
            np.savez_compressed(args.output_base + ".t" + str(idx), x=x)
            all_feats = []
        nlines = nlines + 1

if all_feats:
    print("The last one has %d" % (nlines - 1))
    x = np.array(all_feats)
    np.savez_compressed(args.output_base + ".t" + str(idx), x=x)
