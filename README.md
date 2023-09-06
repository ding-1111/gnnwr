# gnnwr

![PyPI - License](https://img.shields.io/pypi/l/gnnwr)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gnnwr)
[![PyPI - Version](https://img.shields.io/pypi/v/gnnwr)](https://pypi.org/project/gnnwr/)
[![GitHub all releases](https://img.shields.io/github/downloads/zjuwss/gnnwr/total)](https://github.com/zjuwss/gnnwr/releases)

A pytorch implementation of the Geographically Neural Network Weighted Regression (GNNWR) and its derived models

This repository contains:

1. Source code of GNNWR, GTNNWR model and other derived models
2. Tutorial notebooks of how to use these model
3. Released Python wheels

## Table of Contents

- [Models](#models)
- [Install](#install)
- [Usage](#usage)
- [Reference](#reference)
- [Contributing](#contributing)
- [License](#license)

## Models

- [GNNWR](https://doi.org/10.1080/13658816.2019.1707834): Geographically neural network weighted regression, a model address spatial non-stationarity in various domains with complex geographical processes. A spatially weighted neural network (SWNN) is proposed to represent the nonstationary weight matrix.
<p align="center">
<img title="GNNWR" src="assets/The_estimation_process_of_GNNWR_model.jpeg" alt="GNNWR" width=75%>
</p>

- [GTNNWR](https://doi.org/10.1080/13658816.2020.1775836): Geographically and temporally neural network weighted regression, a model for estimating spatiotemporal non-stationary relationships.
Due to the existence of spatiotemporal non-stationary, the spatial relationships of features exhibit significant differences with changes in spatiotemporal structure.
The calculation of spatiotemporal distance is an important aspect of solving spatiotemporal non-stationary problems. 
Therefore, this model introduces spatiotemporal distance into the GNNWR model and proposes a spatiotemporal proximity neural network (STPNN) to accurately calculate spatiotemporal distance. 
Collaborate with SWNN in the GNNWR model to calculate the spatiotemporal non-stationary weight matrix, thereby achieving accurate modeling of spatiotemporal non-stationary relationships.


<p align="center">
<img title="GTNNWR" src="assets/The_estimation_process_of_GTNNWR_model.jpeg" alt="GTNNWR" width=75%>
</p>

## Install

**⚠ If you want to run gnnwr with your GPU, make sure you have installed *pytorch with CUDA support* beforehead:**

For example, a torch 1.13.1 with cuda 11.7:

``` bash
> pip list | grep torch
torch                   1.13.1+cu117
```

You can find install support on [Pytorch's official website](https://pytorch.org/)  for installing the right version that suits your environment.

**⚠ If you only want to run gnnwr with your CPU, or you have already installed the correct version of pytorch:**

Using pip to install gnnwr:  

```
pip install gnnwr
```

## Usage

We provide a series of encapsulated methods and predefined default parameters, users only need to use to load dataset with `pandas` , and call the functions in `gnnwr` package to complete the regression:

```python
from gnnwr import models,datasets
import pandas as pd

data = pd.read_csv('your_data.csv')

train_dataset, val_dataset, test_dataset = datasets.init_dataset(data=data,
                                                                 test_ratio=0.2, valid_ratio=0.1,
                                                                 x_column=['x1', 'x2'], y_column=['y'],
                                                                 spatial_column=['u', 'v'])

gnnwr = models.GNNWR(train_dataset, val_dataset, test_dataset)

gnnwr.run(100)
```

For other uses of customization, the [demos](https://github.com/zjuwss/gnnwr/tree/main/demo) can be referred to.

## Reference

### algorithm  

1. Du, Z., Wang, Z., Wu, S., Zhang, F., and Liu, R., 2020. Geographically neural network weighted regression for the accurate estimation of spatial non-stationarity. International Journal of Geographical Information Science, 34 (7), 1353–1377.  
2. Wu, S., Wang, Z., Du, Z., Huang, B., Zhang, F., and Liu, R., 2021. Geographically and temporally neural network weighted regression for modeling spatiotemporal non-stationary relationships. International Journal of Geographical Information Science, 35 (3), 582–608.


### case study demo
1. Jin Qi, Zhenhong Du, Sensen Wu, Yijun Chen, Yuanyuan Wang, 2023. A spatiotemporally weighted intelligent method for exploring fine-scale distributions of surface dissolved silicate in coastal seas. Science of The Total Environment, 886 , 163981.

## Contributing

### Contributors

<a href="https://github.com/zjuwss/gnnwr/graphs/contributors"><img src="https://contrib.rocks/image?repo=zjuwss/gnnwr" /></a>


## License
[GPLv3 license](https://github.com/zjuwss/gnnwr/blob/main/LICENSE)


