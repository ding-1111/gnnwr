import json
import os

import numpy as np
import pandas
import pandas as pd
import torch
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from torch.utils.data import Dataset, DataLoader


class baseDataset(Dataset):
    def __init__(self, data=None, x_column=None, y_column=None, id_column=None, is_need_STNN=False):
        """
        :param data: DataSets with x_column and y_column
        :param x_column: independent variables column name
        :param y_column: dependent variables column name
        :param is_need_STNN: whether to use STNN
        """
        self.dataframe = data
        self.x = x_column
        self.y = y_column
        self.id = id_column
        if data is None:
            self.x_data = None
            self.datasize = -1
            self.coefsize = -1
            self.y_data = None
            self.id_data = None
        else:
            self.x_data = data[x_column].astype(np.float32).values  # x_data is independent variables data
            self.datasize = self.x_data.shape[0]  # datasize is the number of samples
            self.coefsize = len(x_column) + 1  # coefsize is the number of coefficients
            self.y_data = data[y_column].astype(np.float32).values  # y_data is dependent variables data
            if id_column is not None:
                self.id_data = data[id_column].astype(np.int64).values
            else:
                raise ValueError("id_column is None")
        self.is_need_STNN = is_need_STNN
        self.scale_fn = None  # scale function
        self.x_scale_info = None  # scale information of x_data
        self.y_scale_info = None  # scale information of y_data
        self.distances = None  # distances is the distance matrix of spatial/spatio-temporal data
        self.temporal = None  # temporal is the temporal distance matrix of spatio-temporal data
        self.distances_scale_params = None  # scale parameters of distances

    def __len__(self):
        """
        :return: the number of samples
        """
        return len(self.y_data)

    def __getitem__(self, index):
        """
        :param index: the index of sample
        :return: the index-th distance matrix and the index-th sample
        """
        if self.is_need_STNN:
            return torch.cat((torch.tensor(self.distances[index], dtype=torch.float),
                              torch.tensor(self.temporal[index], dtype=torch.float)), dim=-1), \
                torch.tensor(self.x_data[index], dtype=torch.float), \
                torch.tensor(self.y_data[index], dtype=torch.float), \
                torch.tensor(self.id_data[index], dtype=torch.float)
        return torch.tensor(self.distances[index], dtype=torch.float), torch.tensor(self.x_data[index],
                                                                                    dtype=torch.float), torch.tensor(
            self.y_data[index], dtype=torch.float), torch.tensor(self.id_data[index], dtype=torch.float)

    def scale(self, scale_fn=None, scale_params=None):
        """
        :param scale_fn: scale function
        :param scale_params: scale parameters like MinMaxScaler or StandardScaler
        :return:
        """
        if scale_fn == "minmax_scale":
            self.scale_fn = "minmax_scale"
            x_scale_params = scale_params[0]
            # y_scale_params = scale_params[1]
            self.x_scale_info = {"min": x_scale_params.data_min_, "max": x_scale_params.data_max_}
            self.x_data = x_scale_params.transform(pd.DataFrame(self.x_data, columns=self.x))
            # self.y_scale_info = {"min": y_scale_params.data_min_, "max": y_scale_params.data_max_}
            # self.y_data = y_scale_params.transform(pd.DataFrame(self.y_data, columns=self.y))
        elif scale_fn == "standard_scale":
            self.scale_fn = "standard_scale"
            x_scale_params = scale_params[0]
            # y_scale_params = scale_params[1]
            self.x_scale_info = {"mean": x_scale_params.mean_, "var": x_scale_params.var_}
            self.x_data = x_scale_params.transform(pd.DataFrame(self.x_data, columns=self.x))
            # self.y_scale_info = {"mean": y_scale_params.mean_, "var": y_scale_params.var_}
            # self.y_data = y_scale_params.transform(pd.DataFrame(self.y_data, columns=self.y))

        self.getScaledDataframe()

        self.x_data = np.concatenate((self.x_data, np.ones(
            (self.datasize, 1))), axis=1)

    def scale2(self, scale_fn, scale_params):
        if scale_fn == "minmax_scale":
            self.scale_fn = "minmax_scale"
            x_scale_params = scale_params[0]
            y_scale_params = scale_params[1]
            self.x_data = self.x_data * (x_scale_params["max"] - x_scale_params["min"]) + x_scale_params["min"]
            self.y_data = self.y_data * (y_scale_params["max"] - y_scale_params["min"]) + y_scale_params["min"]
        elif scale_fn == "standard_scale":
            self.scale_fn = "standard_scale"
            x_scale_params = scale_params[0]
            y_scale_params = scale_params[1]
            self.x_data = self.x_data * np.sqrt(x_scale_params["var"]) + x_scale_params["mean"]
            self.y_data = self.y_data * np.sqrt(y_scale_params["var"]) + y_scale_params["mean"]

        self.getScaledDataframe()

        self.x_data = np.concatenate((self.x_data, np.ones(
            (self.datasize, 1))), axis=1)

    def getScaledDataframe(self):
        columns = np.concatenate((self.x, self.y), axis=0)
        scaledData = np.concatenate((self.x_data, self.y_data), axis=1)
        self.scaledDataframe = pd.DataFrame(scaledData, columns=columns)

    def rescale(self, x, y):
        """
        :param x: 输入属性数据
        :param y: 输出属性数据
        :return: 预处理后的输入属性数据、输出属性数据
        """
        if self.scale_fn == "minmax_scale":
            x = np.multiply(x, self.x_scale_info["max"] - self.x_scale_info["min"]) + self.x_scale_info["min"]
            y = np.multiply(y, self.y_scale_info["max"] - self.y_scale_info["min"]) + self.y_scale_info["min"]
        elif self.scale_fn == "standard_scale":
            x = np.multiply(x, np.sqrt(self.x_scale_info["var"])) + self.x_scale_info["mean"]
            y = np.multiply(y, np.sqrt(self.y_scale_info["var"])) + self.y_scale_info["mean"]
        else:
            raise ValueError("invalid process_fn")
        return x, y

    def save(self, dirname):
        if os.path.exists(dirname):
            raise ValueError("dir is already exists")
        if self.dataframe is None:
            raise ValueError("dataframe is None")
        os.makedirs(dirname)
        x_scale_info = {}
        y_scale_info = {}
        for key, value in self.x_scale_info.items():
            x_scale_info[key] = value.tolist()
        for key, value in self.y_scale_info.items():
            y_scale_info[key] = value.tolist()
        # save the information of dataset
        with open(os.path.join(dirname, "dataset_info.json"), "w") as f:
            json.dump({"x": self.x, "y": self.y, "id": self.id,
                       "is_need_STNN": self.is_need_STNN, "scale_fn": self.scale_fn,
                       "x_scale_info": json.dumps(x_scale_info), "y_scale_info": json.dumps(y_scale_info),
                       "distance_scale_info": json.dumps(self.distances_scale_param)
                       }, f)
        # save the distance matrix
        np.save(os.path.join(dirname, "distances.npy"), self.distances)
        # save dataframe
        self.dataframe.to_csv(os.path.join(dirname, "dataframe.csv"), index=False)
        self.scaledDataframe.to_csv(os.path.join(dirname, "scaledDataframe.csv"), index=False)

    def read(self, dirname):
        if not os.path.exists(dirname):
            raise ValueError("dir is not exists")
        # read the information of dataset
        with open(os.path.join(dirname, "dataset_info.json"), "r") as f:
            dataset_info = json.load(f)
        self.x = dataset_info["x"]
        self.y = dataset_info["y"]
        self.id = dataset_info["id"]
        self.is_need_STNN = dataset_info["is_need_STNN"]
        self.scale_fn = dataset_info["scale_fn"]
        self.x_scale_info = json.loads(dataset_info["x_scale_info"])
        self.y_scale_info = json.loads(dataset_info["y_scale_info"])
        self.distances_scale_param = json.loads(dataset_info["distance_scale_info"])
        x_scale_info = self.x_scale_info
        y_scale_info = self.y_scale_info
        for key, value in x_scale_info.items():
            x_scale_info[key] = np.array(value)
        for key, value in y_scale_info.items():
            y_scale_info[key] = np.array(value)
        # read the distance matrix
        self.distances = np.load(os.path.join(dirname, "distances.npy")).astype(np.float32)
        # read dataframe
        self.dataframe = pd.read_csv(os.path.join(dirname, "dataframe.csv")).astype(np.float32)
        self.x_data = self.dataframe[self.x].astype(np.float32).values
        self.datasize = self.x_data.shape[0]
        self.y_data = self.dataframe[self.y].astype(np.float32).values
        self.id_data = self.dataframe[self.id].astype(np.int64).values
        self.coefsize = len(self.x) + 1
        self.scale2(self.scale_fn, [self.x_scale_info, self.y_scale_info])


# wss 这个类是什么用的？
class predictDataset(Dataset):
    def __init__(self, data, x_column, process_fn="minmax_scale", scale_info=[], is_need_STNN=False):
        """
        :param data: 数据集
        :param x_column: 输入属性列名
        :param process_fn: 数据预处理函数
        :process_params: 数据预处理参数（如最大最小值、均值方差等）
        :param is_need_STNN: 是否需要STNN
        """
        data = data.astype(np.float32)
        self.dataframe = data
        self.x = x_column
        self.x_data = data[x_column].values  # x_data is independent variables data
        self.datasize = self.x_data.shape[0]  # datasize is the number of samples
        self.coefsize = len(x_column) + 1  # coefsize is dependent variables data
        self.is_need_STNN = is_need_STNN
        self.process_fn = process_fn
        if len(scale_info):
            self.scale_info_x = scale_info[0]  # scale information of x_data
            self.scale_info_y = scale_info[1]  # scale information of y_data
            self.use_scale_info = True
        else:
            self.use_scale_info = False
        # 数据预处理
        if process_fn == "minmax_scale":
            self.scale_fn = "minmax_scale"
            # stander = MinMaxScaler()
            # self.x_data = stander.fit_transform(self.x_data)
            if self.use_scale_info:
                self.x_data = self.minmax_scaler(self.x_data, self.scale_info_x[0], self.scale_info_x[1])
            else:
                self.x_data = self.minmax_scaler(self.x_data)
        elif process_fn == "standard_scale":
            self.scale_fn = "standard_scale"
            # stander = StandardScaler()
            # self.x_data = stander.fit_transform(self.x_data)
            if self.use_scale_info:
                self.x_data = self.standard_scaler(self.x_data, self.scale_info_x[0], self.scale_info_x[1])
            else:
                self.x_data = self.standard_scaler(self.x_data)

        else:
            raise ValueError("invalid process_fn")

        self.x_data = np.concatenate((self.x_data, np.ones(
            (self.datasize, 1))), axis=1)

        self.distances = None
        self.temporal = None

    def __len__(self):
        """
        :return: 数据集大小
        """
        return len(self.x_data)

    def __getitem__(self, index):
        """
        :param index: 数据索引
        :return: 距离矩阵、输入属性数据、输出属性数据
        """
        if self.is_need_STNN:
            return torch.cat((torch.tensor(self.distances[index], dtype=torch.float),
                              torch.tensor(self.temporal[index], dtype=torch.float)), dim=-1), torch.tensor(
                self.x_data[index], dtype=torch.float)
        return torch.tensor(self.distances[index], dtype=torch.float), torch.tensor(self.x_data[index],
                                                                                    dtype=torch.float)

    def rescale(self, x):
        """
        :param x: 输入属性数据
        :return: 预处理后的输入属性数据、输出属性数据
        """
        if self.scale_fn == "minmax_scale":
            x = x * (self.scale_info_y[1] - self.scale_info_y[0]) + self.scale_info_y[0]
        elif self.scale_fn == "standard_scale":
            x = x * np.sqrt(self.scale_info_y[1]) + self.scale_info_y[0]
        else:
            raise ValueError("invalid process_fn")

        return x

    def minmax_scaler(self, x, min=[], max=[]):
        if len(min) == 0:
            x = (x - x.min(axis=0)) / (x.max(axis=0) - x.min(axis=0))
        else:
            x = (x - min) / (max - min)
        return x

    def standard_scaler(self, x, mean=[], std=[]):
        if len(mean) == 0:
            x = (x - x.mean(axis=0)) / x.std(axis=0)
        else:
            x = (x - mean) / std
        return x

    # def generatePredictData(self, x, y):
    #     """
    #     :param x: 输入属性数据
    #     :param y: 输出属性数据
    #     :return: 预处理后的输入属性数据、输出属性数据
    #     """
    #     if self.scale_fn == "minmax_scale":
    #         x = (x - self.x_scale_info["min"]) / (self.x_scale_info["max"] - self.x_scale_info["min"])
    #         y = (y - self.y_scale_info["min"]) / (self.y_scale_info["max"] - self.y_scale_info["min"])
    #     elif self.scale_fn == "standard_scale":
    #         x = (x - self.x_scale_info["mean"]) / np.sqrt(self.x_scale_info["var"])
    #         y = (y - self.y_scale_info["mean"]) / np.sqrt(self.y_scale_info["var"])
    #     else:
    #         raise ValueError("invalid process_fn")
    #     x = np.concatenate((x, np.ones((x.shape[0], 1))), axis=1)
    #     return x, y


def BasicDistance(x, y):
    """
    :param x: 输入点坐标数据
    :param y: 输入训练集点坐标数据
    :return: 距离矩阵
    """
    return np.float32(np.sqrt(np.sum((x[:, np.newaxis, :] - y) ** 2, axis=2)))


def Manhattan_distance(x, y):
    """
    :param x: 输入点坐标数据
    :param y: 输入训练集点坐标数据
    :return: 距离矩阵
    """
    return np.float32(np.sum(np.abs(x[:, np.newaxis, :] - y), axis=2))


def init_dataset(data, test_ratio, valid_ratio, x_column, y_column, spatial_column=None, temp_column=None,
                 id_column=None, sample_seed=100, process_fn="minmax_scale", batch_size=32, shuffle=True,
                 use_class=baseDataset,
                 spatial_fun=BasicDistance, temporal_fun=Manhattan_distance, max_val_size=-1, max_test_size=-1,
                 from_for_cv=0, is_need_STNN=False, Reference=None, simple_distance=True):
    """
    :param data: dataset
    :param test_ratio: test data ratio
    :param valid_ratio: valid data ratio
    :param x_column: input attribute column name
    :param y_column: output attribute column name
    :param spatial_column: spatial attribute column name
    :param temp_column: temporal attribute column name
    :param sample_seed: random seed
    :param process_fn: data pre-process function
    :param batch_size: batch size
    :param max_val_size: max valid data size in one injection
    :param max_test_size: max test data size in one injection
    :param shuffle: shuffle data
    :param use_class: dataset class
    :param spatial_fun: spatial distance calculate function
    :param temporal_fun: temporal distance calculate function
    :param from_for_cv: the start index of the data for cross validation
    :param is_need_STNN: whether to use STNN
    :param Reference: reference points to calculate the distance
    :param simple_distance: whether to use simple distance function to calculate the distance
    :return: train dataset, valid dataset, test dataset
    """
    if spatial_fun is None:
        # if dist_fun is None, raise error
        raise ValueError(
            "dist_fun must be a function that can process the data")

    if spatial_column is None:
        # if dist_column is None, raise error
        raise ValueError(
            "dist_column must be a column name in data")

    if id_column == None:
        if not 'id' in data.columns:
            data['id'] = [i for i in range(data.shape[0])]
            id_column = ['id']
        else:
            raise ValueError("'id' column has been occupied, please offer another column")

    np.random.seed(sample_seed)
    data = data.sample(frac=1)  # shuffle data
    scaler_x = None
    scaler_y = None
    # data pre-process
    if process_fn == "minmax_scale":
        scaler_x = MinMaxScaler()
        scaler_y = MinMaxScaler()
    elif process_fn == "standard_scale":
        scaler_x = StandardScaler()
        scaler_y = StandardScaler()
    scaler_params_x = scaler_x.fit(data[x_column])
    scaler_params_y = scaler_y.fit(data[y_column])
    scaler_params = [scaler_params_x, scaler_params_y]
    if process_fn == "minmax_scale":
        print("x_min:" + str(scaler_params_x.data_min_) + ";  x_max:" + str(scaler_params_x.data_max_))
        print("y_min:" + str(scaler_params_y.data_min_) + ";  y_max:" + str(scaler_params_y.data_max_))
    elif process_fn == "standard_scale":
        print("x_mean:" + str(scaler_params_x.mean_) + ";  x_var:" + str(scaler_params_x.var_))
        print("y_mean:" + str(scaler_params_y.mean_) + ";  y_var:" + str(scaler_params_y.var_))

    # data split
    test_data = data[int((1 - test_ratio) * len(data)):]
    train_data = data[:int((1 - test_ratio) * len(data))]
    val_data = train_data[
               int(from_for_cv * valid_ratio * len(train_data)):int((1 + from_for_cv) * valid_ratio * len(train_data))]
    train_data = pandas.concat([train_data[:int(from_for_cv * valid_ratio * len(train_data))],
                                train_data[int((1 + from_for_cv) * valid_ratio * len(train_data)):]])

    # Use the parameters of the dataset to normalize the train_dataset, val_dataset, and test_dataset
    train_dataset = use_class(train_data, x_column, y_column, id_column, is_need_STNN)
    val_dataset = use_class(val_data, x_column, y_column, id_column, is_need_STNN)
    test_dataset = use_class(test_data, x_column, y_column, id_column, is_need_STNN)
    train_dataset.scale(process_fn, scaler_params)
    val_dataset.scale(process_fn, scaler_params)
    test_dataset.scale(process_fn, scaler_params)

    # wss is_need_STNN参数是做什么用的？
    # wss 计算距离的参照样本点可能要有两种选择：一种是以训练集的点为参考，一种是以训练集+验证集的点为参考
    # wss 因为如果是十折交叉，要以训练集为准的话，得保证这10折的训练集个数是一致的；而如果以训练集+验证集的话，就不用考虑这个问题。从这个
    # 角度来说训练集+验证集作为算距离的参考点更为合适。 添加参数判断？

    if Reference is None:
        reference_data = train_data
    elif isinstance(Reference, str):
        if Reference == "train":
            reference_data = train_data
        elif Reference == "train_val":
            reference_data = pandas.concat([train_data, val_data])
        else:
            raise ValueError("Reference str must be 'train' or 'train_val'")
    else:
        reference_data = Reference
    if not isinstance(reference_data, pandas.DataFrame):
        raise ValueError("reference_data must be a pandas.DataFrame")
    train_dataset.reference, val_dataset.reference, test_dataset.reference = reference_data, reference_data, reference_data
    if not is_need_STNN:
        if simple_distance:
            # if not use STNN, calculate spatial/temporal distance matrix and concatenate them
            train_dataset.distances = spatial_fun(
                train_data[spatial_column].values, reference_data[spatial_column].values)  # 计算train距离矩阵
            val_dataset.distances = spatial_fun(
                val_data[spatial_column].values, reference_data[spatial_column].values)  # 计算val距离矩阵
            test_dataset.distances = spatial_fun(
                test_data[spatial_column].values, reference_data[spatial_column].values)  # 计算test距离矩阵

            if temp_column is not None:
                # if temp_column is not None, calculate temporal distance matrix
                train_dataset.temporal = temporal_fun(
                    train_data[temp_column].values, reference_data[temp_column].values)
                val_dataset.temporal = temporal_fun(
                    val_data[temp_column].values, reference_data[temp_column].values)
                test_dataset.temporal = temporal_fun(
                    test_data[temp_column].values, reference_data[temp_column].values)

                train_dataset.distances = np.concatenate(
                    (train_dataset.distances[:, :, np.newaxis], train_dataset.temporal[:, :, np.newaxis]),
                    axis=2)  # concatenate spatial and temporal distance matrix
                val_dataset.distances = np.concatenate(
                    (val_dataset.distances[:, :, np.newaxis], val_dataset.temporal[:, :, np.newaxis]), axis=2)
                test_dataset.distances = np.concatenate(
                    (test_dataset.distances[:, :, np.newaxis], test_dataset.temporal[:, :, np.newaxis]), axis=2)
        else:
            train_dataset.distances = np.repeat(train_data[spatial_column].values[:, np.newaxis, :],
                                                len(reference_data),
                                                axis=1)
            train_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :],
                                            train_dataset.datasize,
                                            axis=1)
            train_dataset.distances = np.concatenate(
                (train_dataset.distances, np.transpose(train_temp_distance, (1, 0, 2))), axis=2)

            val_dataset.distances = np.repeat(val_data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                              axis=1)
            val_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :], val_dataset.datasize,
                                          axis=1)
            val_dataset.distances = np.concatenate((val_dataset.distances, np.transpose(val_temp_distance, (1, 0, 2))),
                                                   axis=2)

            test_dataset.distances = np.repeat(test_data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                               axis=1)
            test_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :],
                                           test_dataset.datasize,
                                           axis=1)
            test_dataset.distances = np.concatenate(
                (test_dataset.distances, np.transpose(test_temp_distance, (1, 0, 2))), axis=2)
            # if temp_column is not None, calculate temporal point matrix
            if temp_column is not None:
                train_dataset.temporal = np.repeat(train_data[temp_column].values[:, np.newaxis, :],
                                                   len(reference_data),
                                                   axis=1)
                train_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                                train_dataset.datasize,
                                                axis=1)
                train_dataset.temporal = np.concatenate(
                    (train_dataset.temporal, np.transpose(train_temp_temporal, (1, 0, 2))), axis=2)

                val_dataset.temporal = np.repeat(val_data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                                 axis=1)
                val_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                              val_dataset.datasize,
                                              axis=1)
                val_dataset.temporal = np.concatenate(
                    (val_dataset.temporal, np.transpose(val_temp_temporal, (1, 0, 2))),
                    axis=2)

                test_dataset.temporal = np.repeat(test_data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                                  axis=1)
                test_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                               test_dataset.datasize,
                                               axis=1)
                test_dataset.temporal = np.concatenate(
                    (test_dataset.temporal, np.transpose(test_temp_temporal, (1, 0, 2))), axis=2)
            train_dataset.distances = np.concatenate(
                (train_dataset.distances, train_dataset.temporal), axis=2)
            val_dataset.distances = np.concatenate(
                (val_dataset.distances, val_dataset.temporal), axis=2)
            test_dataset.distances = np.concatenate(
                (test_dataset.distances, test_dataset.temporal), axis=2)
    else:
        # if use STNN, calculate spatial/temporal point matrix
        train_dataset.distances = np.repeat(train_data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                            axis=1)
        train_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :], train_dataset.datasize,
                                        axis=1)
        train_dataset.distances = np.concatenate(
            (train_dataset.distances, np.transpose(train_temp_distance, (1, 0, 2))), axis=2)

        val_dataset.distances = np.repeat(val_data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                          axis=1)
        val_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :], val_dataset.datasize,
                                      axis=1)
        val_dataset.distances = np.concatenate((val_dataset.distances, np.transpose(val_temp_distance, (1, 0, 2))),
                                               axis=2)

        test_dataset.distances = np.repeat(test_data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                           axis=1)
        test_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :], test_dataset.datasize,
                                       axis=1)
        test_dataset.distances = np.concatenate(
            (test_dataset.distances, np.transpose(test_temp_distance, (1, 0, 2))), axis=2)
        # if temp_column is not None, calculate temporal point matrix
        if temp_column is not None:
            train_dataset.temporal = np.repeat(train_data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                               axis=1)
            train_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                            train_dataset.datasize,
                                            axis=1)
            train_dataset.temporal = np.concatenate(
                (train_dataset.temporal, np.transpose(train_temp_temporal, (1, 0, 2))), axis=2)

            val_dataset.temporal = np.repeat(val_data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                             axis=1)
            val_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :], val_dataset.datasize,
                                          axis=1)
            val_dataset.temporal = np.concatenate((val_dataset.temporal, np.transpose(val_temp_temporal, (1, 0, 2))),
                                                  axis=2)

            test_dataset.temporal = np.repeat(test_data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                              axis=1)
            test_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :], test_dataset.datasize,
                                           axis=1)
            test_dataset.temporal = np.concatenate(
                (test_dataset.temporal, np.transpose(test_temp_temporal, (1, 0, 2))), axis=2)
    train_dataset.simple_distance = simple_distance
    # initialize dataloader for train/val/test dataset
    # set batch_size for train_dataset as batch_size
    # set batch_size for val_dataset as max_val_size
    # set batch_size for test_dataset as max_test_size
    if max_val_size < 0: max_val_size = len(val_dataset)
    if max_test_size < 0: max_test_size = len(test_dataset)
    if process_fn == "minmax_scale":
        distance_scale = MinMaxScaler()
    else:
        distance_scale = StandardScaler()
    # scale distance matrix
    train_distance_len = len(train_dataset.distances)
    val_distance_len = len(val_dataset.distances)
    distances = np.concatenate((train_dataset.distances, val_dataset.distances, test_dataset.distances), axis=0)
    distances = distance_scale.fit_transform(distances.reshape(-1, distances.shape[-1])).reshape(distances.shape)
    if process_fn == "minmax_scale":
        distance_scale_param = {"min": distance_scale.data_min_, "max": distance_scale.data_max_}
    else:
        distance_scale_param = {"mean": distance_scale.mean_, "var": distance_scale.var_}
    train_dataset.distances = distances[:train_distance_len]
    val_dataset.distances = distances[train_distance_len:train_distance_len + val_distance_len]
    test_dataset.distances = distances[train_distance_len + val_distance_len:]
    train_dataset.distances_scale_param = val_dataset.distances_scale_param = test_dataset.distances_scale_param = distance_scale_param
    train_dataset.dataloader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=shuffle)
    val_dataset.dataloader = DataLoader(
        val_dataset, batch_size=max_val_size, shuffle=shuffle)
    test_dataset.dataloader = DataLoader(
        test_dataset, batch_size=max_test_size, shuffle=shuffle)

    return train_dataset, val_dataset, test_dataset


def init_dataset_cv(data, test_ratio, k_fold, x_column, y_column, spatial_column=None, temp_column=None,
                    sample_seed=100,
                    process_fn="minmax_scale", batch_size=32, shuffle=True, use_class=baseDataset,
                    spatial_fun=BasicDistance, temporal_fun=Manhattan_distance, max_val_size=-1, max_test_size=-1):
    """

    :param data: input data
    :param test_ratio: test set ratio
    :param k_fold:  k of k-fold
    :param x_column: attribute column name
    :param y_column: label column name
    :param spatial_column: spatial distance column name
    :param temp_column: temporal distance column name
    :param sample_seed: random seed
    :param process_fn: data process function
    :param batch_size: batch size
    :param shuffle: shuffle or not
    :param use_class: dataset class
    :param spatial_fun: spatial distance calculate function
    :param temporal_fun: temporal distance calculate function
    :param max_val_size: validation set size
    :param max_test_size: test set size
    :return: cv_data_set, test_dataset
    """
    cv_data_set = []
    valid_ratio = (1 - test_ratio) / k_fold
    test_dataset = None
    for i in range(k_fold):
        train_dataset, val_dataset, test_dataset = init_dataset(data, test_ratio, valid_ratio, x_column, y_column,
                                                                spatial_column,
                                                                temp_column,
                                                                sample_seed,
                                                                process_fn, batch_size, shuffle, use_class,
                                                                spatial_fun, temporal_fun, max_val_size, max_test_size,
                                                                from_for_cv=i)
        cv_data_set.append((train_dataset, val_dataset))
    return cv_data_set, test_dataset


# TODO 这里的归一化和上面的不一样，需要修改
def init_dataset_with_dist_frame(data, train_ratio, valid_ratio, x_column, y_column, id_column, dist_frame=None,
                                 process_fn="minmax_scale", batch_size=32, shuffle=True, use_class=baseDataset):
    train_data, val_data, test_data = np.split(data.sample(frac=1),
                                               [int(train_ratio * len(data)),
                                                int((train_ratio + valid_ratio) * len(data))])  # 划分数据集

    # wss 这三个数据集的归一化方式应该要保持一致的（最大值、最小值等，可以考虑整个数据集的特征），这里的结果会有问题
    # 初始化train_dataset,val_dataset,test_dataset
    train_dataset = use_class(train_data, x_column, y_column, process_fn)
    val_dataset = use_class(val_data, x_column, y_column, process_fn)
    test_dataset = use_class(test_data, x_column, y_column, process_fn)

    dist_frame.columns = ['id1', 'id2', 'dis']
    dist_frame = dist_frame.set_index(['id1', 'id2'])[
        'dis'].unstack().reset_index().drop('id1', axis=1)

    train_ids = train_data[id_column[0]].tolist()
    val_ids = val_data[id_column[0]].tolist()
    test_ids = test_data[id_column[0]].tolist()

    train_dataset.distances = np.float32(
        dist_frame[dist_frame.index.isin(train_ids)][train_ids].values)
    val_dataset.distances = np.float32(
        dist_frame[dist_frame.index.isin(val_ids)][train_ids].values)
    test_dataset.distances = np.float32(
        dist_frame[dist_frame.index.isin(test_ids)][train_ids].values)

    train_dataset.dataloader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=shuffle)
    val_dataset.dataloader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=shuffle)
    test_dataset.dataloader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=shuffle)

    return train_dataset, val_dataset, test_dataset


def init_predict_dataset(data, train_dataset, x_column, spatial_column=None, temp_column=None,
                         process_fn="minmax_scale", scale_sync=True, use_class=predictDataset,
                         spatial_fun=BasicDistance, temporal_fun=Manhattan_distance, max_size=-1, is_need_STNN=False):
    """
    :param data: 输入预测数据
    :param train_data: 输入训练数据集
    :param x_column: 输入属性列名
    :param spatial_column: 距离属性列名
    :param temp_column: 时间距离属性列名
    :param process_fn: 数据预处理函数
    :param scale_sync: 是否用训练集相同的缩放参数
    :param max_size: 一次注入最大预测数据大小
    :param use_class: 使用的数据集类
    :param spatial_fun: 距离计算函数
    :param temporal_fun: 时间距离计算函数
    :param is_need_STNN: 是否需要STNN
    :return: 预测数据集
    """
    if spatial_fun is None:
        # if dist_fun is None, raise error
        raise ValueError(
            "dist_fun must be a function that can process the data")

    if spatial_column is None:
        # if dist_column is None, raise error
        raise ValueError(
            "dist_column must be a column name in data")

    # initialize the predict_dataset
    if train_dataset.scale_fn == "minmax_scale":
        process_params = [[train_dataset.x_scale_info['min'], train_dataset.x_scale_info['max']],
                          [train_dataset.y_scale_info['min'], train_dataset.y_scale_info['max']]]
    elif train_dataset.scale_fn == "standard_scale":
        process_params = [[train_dataset.x_scale_info['mean'], train_dataset.x_scale_info['std']],
                          [train_dataset.y_scale_info['mean'], train_dataset.y_scale_info['std']]]
    else:
        raise ValueError("scale_fn must be minmax_scale or standard_scale")
    # print("ProcessParams:",process_params)
    if scale_sync:
        predict_dataset = use_class(data=data, x_column=x_column, process_fn=process_fn, scale_info=process_params,
                                    is_need_STNN=is_need_STNN)
    else:
        predict_dataset = use_class(data=data, x_column=x_column, process_fn=process_fn, is_need_STNN=is_need_STNN)

    # train_data = train_dataset.dataframe
    reference_data = train_dataset.reference

    if not is_need_STNN:
        # if not use STNN, calculate spatial/temporal distance matrix and concatenate them
        if train_dataset.simple_distance:
            predict_dataset.distances = spatial_fun(
                data[spatial_column].values, reference_data[spatial_column].values)

            if temp_column is not None:
                # if temp_column is not None, calculate temporal distance matrix
                predict_dataset.temporal = temporal_fun(
                    data[temp_column].values, reference_data[temp_column].values)

                predict_dataset.distances = np.concatenate(
                    (predict_dataset.distances[:, :, np.newaxis], predict_dataset.temporal[:, :, np.newaxis]),
                    axis=2)  # concatenate spatial and temporal distance matrix
        else:
            predict_dataset.distances = np.repeat(data[spatial_column].values[:, np.newaxis, :],
                                                  len(reference_data),
                                                  axis=1)
            predict_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :],
                                              predict_dataset.datasize,
                                              axis=1)
            predict_dataset.distances = np.concatenate(
                (predict_dataset.distances, np.transpose(predict_temp_distance, (1, 0, 2))), axis=2)

            if temp_column is not None:
                predict_dataset.temporal = np.repeat(data[temp_column].values[:, np.newaxis, :],
                                                     len(reference_data),
                                                     axis=1)
                predict_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                                  predict_dataset.datasize,
                                                  axis=1)
                predict_dataset.temporal = np.concatenate(
                    (predict_dataset.temporal, np.transpose(predict_temp_temporal, (1, 0, 2))), axis=2)
            predict_dataset.distances = np.concatenate(
                (predict_dataset.distances, predict_dataset.temporal), axis=2)

    else:
        # if use STNN, calculate spatial/temporal point matrix
        # spatial distances matrix
        predict_dataset.distances = np.repeat(data[spatial_column].values[:, np.newaxis, :], len(reference_data),
                                              axis=1)
        predict_temp_distance = np.repeat(reference_data[spatial_column].values[:, np.newaxis, :],
                                          predict_dataset.datasize,
                                          axis=1)
        predict_dataset.distances = np.concatenate(
            (predict_dataset.distances, np.transpose(predict_temp_distance, (1, 0, 2))), axis=2)

        # temporal distances matrix
        if temp_column is not None:
            predict_dataset.temporal = np.repeat(data[temp_column].values[:, np.newaxis, :], len(reference_data),
                                                 axis=1)
            predict_temp_temporal = np.repeat(reference_data[temp_column].values[:, np.newaxis, :],
                                              predict_dataset.datasize,
                                              axis=1)
            predict_dataset.temporal = np.concatenate(
                (predict_dataset.temporal, np.transpose(predict_temp_temporal, (1, 0, 2))), axis=2)
    if process_fn == "minmax_scale":
        predict_dataset.distances = predict_dataset.minmax_scaler(predict_dataset.distances,
                                                                  train_dataset.distances_scale_param['min'],
                                                                  train_dataset.distances_scale_param['max'])
    else:
        predict_dataset.distances = predict_dataset.standard_scaler(predict_dataset.distances,
                                                                    train_dataset.distances_scale_param['mean'],
                                                                    train_dataset.distances_scale_param['var'])
    # initialize dataloader for train/val/test dataset
    if max_size < 0: max_size = len(predict_dataset)
    predict_dataset.dataloader = DataLoader(
        predict_dataset, batch_size=max_size, shuffle=False)

    return predict_dataset
