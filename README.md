# CLAR (Temporary Name)
### Tool for malware code analysis based on the paper '---'

Repository to replicate the experiments presented in '---' by Iadarola G. et al.

If you are using this repository, please consider [**citing our works**](#publications) (see links at the end of this README file).

This repository contains the code to strictly replicate the experiments, but it is based on the [TAMI](https://github.com/Djack1010/tami) repository, which constitute the main repository.

## Getting Started

##### Ubuntu 20.04

You can run the script `install.sh` to set up all the necessary dependencies (excluding the GPU ones).
Then, you should install all the necessary libraries with `pip`
```
pip install -r requirements.txt 
```

##### Run in Docker container (Suggested for experimenting on GPU)
<a name="run_docker"></a>

You can run TAMI in a container built upon the `tensorflow/tensorflow:latest-gpu` image. This is strongly suggested for handling dependencies related to GPU drivers, because you only need to install [Docker](https://docs.docker.com/install/) and the [NVIDIA Docker support](https://github.com/NVIDIA/nvidia-docker) to work with the Tensorflow GPU support (see also [Tensorflow Docker Requirements](https://www.tensorflow.org/install/docker) for further instructions).

In the `docker/` folder of this repository, there is a Dockerfile which build the image and install the requirements for TAMI, and two scripts (`build.sh` and `run_container.sh`) to handle the docker operations.

```
cd docker
./build.sh
./run_container.sh
```
Refers to [TAMI](https://github.com/Djack1010/tami) for further information and documentation on the code.

#### Usage

The tool can be run with the `main.py` script.

`main.py` usage:
```
python main.py --help
usage: main.py [-h] -m {DATA,BASIC_CNN,BASIC_LSTM,BASIC_MLP,NEDO,VINC,VGG16} -d DATASET [-o OUTPUT_MODEL] 
               [-l LOAD_MODEL] [-e EPOCHS] [-b BATCH_SIZE] [-i IMAGE_SIZE] 
               [-w WEIGHTS] [--mode {train-val,train-test,test,gradcam-cati,gradcam-only}] [--exclude_top] 
               [--caching]
```

Logs, figure and performance results are stored in `results` folders.
Tensorboard can be used to print graph of training and validation trend.
```
tensorboard --logdir results/tensorboard/fit/
```

## Authors & References

* **Giacomo Iadarola** - *main contributor* - [Djack1010](https://github.com/Djack1010) giacomo.iadarola(at)iit.cnr.it

<a name="publications"></a>
If you are using this repository, please cite our work by referring to our publications (BibTex format):
```
work in progress...
```

#### Acknowledgements

The authors would like to thank the 'Trust, Security and Privacy' research group within the [Institute of Informatics and Telematics](https://www.iit.cnr.it/) (CNR - Pisa, Italy), that support their researches.


