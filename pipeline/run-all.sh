#!/bin/bash

set -e

[[ $# -lt 1 ]] && echo "Usage: $0 <trace_file>" && exit 1

TRACE_FILE=$1

[[ -f $TRACE_FILE ]] || (echo "Trace file $TRACE_FILE does not exist" && exit 1)
TRACE_FILE=$(realpath $TRACE_FILE)
TRACE_FILE_NAME=$(basename $TRACE_FILE)
TRACE_NAME="${TRACE_FILE_NAME%.*}"
TRACE_FILE_DIR=$(dirname $TRACE_FILE)

cd ../dp
make -s buildROB
make -s buildSim
cd - > /dev/null

cd ../sim
[[ ! -d build ]] && cmake -B build > /dev/null 2>&1
cmake --build build -j $(nproc) > /dev/null
cd - > /dev/null

GENERATED_DIR=$TRACE_FILE_DIR/generated
rm -rf $GENERATED_DIR


# 0. Build ROB
echo "0. Build ROB"
mkdir -p $GENERATED_DIR/0
../dp/buildROB $TRACE_FILE > $GENERATED_DIR/0/$TRACE_NAME.ml
echo "================================"

# 1. Unique
echo "1. Unique"
mkdir -p $GENERATED_DIR/1
../dp/1_unique.py --output $GENERATED_DIR/1/$TRACE_NAME.mlu $GENERATED_DIR/0/$TRACE_NAME.ml
echo "================================"

# 2. ML to NPZ
echo "2. ML to NPZ"
mkdir -p $GENERATED_DIR/2
../dp/2_ml-to-npy.py --output-base $GENERATED_DIR/2/$TRACE_NAME.mlu $GENERATED_DIR/1/$TRACE_NAME.mlu
echo "================================"

# 3. Scale
echo "3. Scale"
mkdir -p $GENERATED_DIR/3
../dp/3_scale.py --save $GENERATED_DIR/2/$TRACE_NAME.mlu.t*.npz --dirName $GENERATED_DIR/3
echo "================================"

# 4. Combine
echo "4. Combine"
mkdir -p $GENERATED_DIR/4
../dp/4_combine.py --output $GENERATED_DIR/4/totalall.npz $GENERATED_DIR/2/$TRACE_NAME.mlu.t*.npz $GENERATED_DIR/3/$TRACE_NAME.mlu.t*.npz
echo "================================"

# 5. Make Sim Input
echo "5. Make Sim Input"
mkdir -p $GENERATED_DIR/5
# You cannot believe the arg -1 is minus one
../dp/make_sim_input.py $GENERATED_DIR/0/$TRACE_NAME.ml -1 $GENERATED_DIR/3/statsall.npz > $GENERATED_DIR/5/$TRACE_NAME.tr
../dp/buildSim $TRACE_FILE 1000 > $GENERATED_DIR/5/$TRACE_NAME.tra
echo "================================"

# 6. Train
echo "6. Train"
mkdir -p $GENERATED_DIR/6
CUDA_VISIBLE_DEVICES=0 python ../ml/train-from-one-file.py --save-model --epochs 10000 --data-name $GENERATED_DIR/4/totalall.npz --stats-name $GENERATED_DIR/3/statsall.npz --save-path $GENERATED_DIR/6 \
    | tee $GENERATED_DIR/6/train.log
echo "================================"

# 7. Test Single
echo "7. Test Single"
mkdir -p $GENERATED_DIR/7
CUDA_VISIBLE_DEVICES=0 python ../ml/train-from-one-file.py --test --data-name $GENERATED_DIR/4/totalall.npz --stats-name $GENERATED_DIR/3/statsall.npz --save-path $GENERATED_DIR/6
echo "================================"

# 8. Convert
echo "8. Convert"
mkdir -p $GENERATED_DIR/8
python ../ml/convert.py $GENERATED_DIR/6 $GENERATED_DIR/8
echo "================================"

BEST=$(cat $GENERATED_DIR/6/train.log | tr '\n' ' ' | awk '{print $NF}')

# 9. Simulate
echo "9. Simulate"
mkdir -p $GENERATED_DIR/9
../sim/build/simulator_ground_truth $GENERATED_DIR/5/$TRACE_NAME.tr $GENERATED_DIR/5/$TRACE_NAME.tra $GENERATED_DIR/8/$BEST.pt.pt $GENERATED_DIR/3/var.txt | tee $GENERATED_DIR/9/simoutput.txt
python ../sim/runsimulations.py $GENERATED_DIR/5/$TRACE_NAME.tr $GENERATED_DIR/5/$TRACE_NAME.tra $GENERATED_DIR/8/ $GENERATED_DIR/3/var.txt $GENERATED_DIR/9/simoutput.txt
echo "================================"
