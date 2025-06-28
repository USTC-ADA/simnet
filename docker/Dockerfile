# from gem5 dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt -y update && apt -y upgrade && \
    apt -y install build-essential git m4 scons zlib1g zlib1g-dev \
        libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev \
        python3-dev doxygen libboost-all-dev libhdf5-serial-dev python3-pydot \
        libpng-dev libelf-dev pkg-config pip python3-venv black

RUN pip install mypy pre-commit \
    # gem5 misses six
    six

# SimNet dependencies
# * tools
RUN apt install -y wget gnupg software-properties-common cmake unzip
RUN pip install ptflops einops sortedcontainers numpy scikit-learn \
    pandas matplotlib plotext terminalplot xgboost ipython

# * Python already installed
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 310

# * Pytorch: CUDA 12.1
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# * CUDA: 12.1
RUN mkdir -p /etc/apt/trusted.gpg.d /etc/apt/sources.list.d && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-archive-keyring.gpg && \
    mv cuda-archive-keyring.gpg /etc/apt/trusted.gpg.d/cuda-archive-keyring.gpg && \
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /" | tee /etc/apt/sources.list.d/cuda.list && \
    apt-get update && \
    apt-get install -y cuda-toolkit-12-1

# * libtorch: 2.5.1 CUDA 12.1
RUN wget https://download.pytorch.org/libtorch/cu121/libtorch-shared-with-deps-2.5.1%2Bcu121.zip && \
    unzip libtorch-shared-with-deps-2.5.1+cu121.zip -d /opt/ && \
    rm libtorch-shared-with-deps-2.5.1+cu121.zip

# create user
ARG USER_NAME=''
ARG USER_ID=''
ARG GROUP_NAME=''
ARG GROUP_ID=''

# fail if USER_NAME, USER_ID, GROUP_NAME, GROUP_ID are not provided
RUN /bin/bash -c "[[ USER_NAME && USER_ID && GROUP_NAME && GROUP_ID ]]" || \
    (echo "USER_NAME, USER_ID, GROUP_NAME, GROUP_ID must be provided" && exit 1)
RUN groupadd -g $GROUP_ID $GROUP_NAME && \
    useradd -m -u $USER_ID -g $GROUP_NAME $USER_NAME

USER $USER_NAME

# really needed?
ENV TORCH_CUDA_ARCH_LIST="8.9"
ENV PATH=/usr/local/cuda/bin:$PATH
