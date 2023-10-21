import math
import statsmodels.api as sm
import pandas as pd
import torch
import warnings
import copy
import folium
from folium.plugins import HeatMap, MarkerCluster
import branca
class OLS():
    """
    OLS is the class to calculate the OLR weights of data.Get the weight by `object.params`.

    :param dataset: Input data
    :param xName: the independent variables' column
    :param yName: the dependent variable's column
    """
    def __init__(self, dataset, xName: list, yName: list):

        self.__dataset = dataset
        self.__xName = xName
        self.__yName = yName
        self.__formula = yName[0] + '~' + '+'.join(xName)
        self.__fit = sm.formula.ols(self.__formula, dataset).fit()
        self.params = list(self.__fit.params.to_dict().values())
        intercept = self.__fit.params[0]
        self.params = self.params[1:]
        self.params.append(intercept)


class DIAGNOSIS:
    # TODO 更多诊断方法
    """
    Diagnosis is the class to calculate the diagnoses of GNNWR/GTNNWR.

    :param weight: output of the neural network
    :param x_data: the independent variables
    :param y_data: the dependent variables
    :param y_pred: output of the GNNWR/GTNNWR
    """
    def __init__(self, weight, x_data, y_data, y_pred):
        self.__weight = weight
        self.__x_data = x_data
        self.__y_data = y_data
        self.__y_pred = y_pred
        self.__n = len(y_data)
        self.__k = len(x_data[0])

        self.__residual = y_data - y_pred
        self.__ssr = torch.sum((y_pred - torch.mean(y_data)) ** 2)

        self.__hat_com = torch.mm(torch.linalg.inv(
            torch.mm(self.__x_data.transpose(-2,-1), self.__x_data)), self.__x_data.transpose(-2,-1))
        self.__ols_hat = torch.mm(self.__x_data, self.__hat_com)
        x_data_tile = x_data.repeat(self.__n, 1)
        x_data_tile = x_data_tile.view(self.__n, self.__n, -1)
        x_data_tile_t = x_data_tile.transpose(1, 2)
        gtweight_3d = torch.diag_embed(self.__weight)
        hatS_temp = torch.matmul(gtweight_3d,
                                 torch.matmul(torch.inverse(torch.matmul(x_data_tile_t, x_data_tile)), x_data_tile_t))
        hatS = torch.matmul(x_data.view(-1, 1, x_data.size(1)), hatS_temp)
        hatS = hatS.view(-1, self.__n)
        self.__hat = hatS
        self.__S = torch.trace(self.__hat)

    def hat(self):
        """
        :return: hat matrix
        """
        return self.__hat

    def F1_GNN(self):
        """
        :return: F1-test
        """
        k1 = self.__n - 2 * torch.trace(self.__hat) + \
             torch.trace(torch.mm(self.__hat.transpose(-2,-1), self.__hat))
        k2 = self.__n - self.__k - 1
        rss_olr = torch.sum(
            (torch.mean(self.__y_data) - torch.mm(self.__ols_hat, self.__y_data)) ** 2)
        return self.__ssr / k1 / (rss_olr / k2)

    def AIC(self):
        """
        :return: AIC
        """
        return self.__n * (math.log(self.__ssr / self.__n * 2 * math.pi, math.e)) + self.__n + self.__k
    def AICc(self):
        """

        :return: AICc
        """
        return self.__n * (math.log(self.__ssr / self.__n * 2 * math.pi, math.e) + (self.__n + self.__S) / (
                self.__n - self.__S - 2))

    def R2(self):
        """

        :return: R2 of the result
        """
        return 1 - torch.sum(self.__residual ** 2) / torch.sum((self.__y_data - torch.mean(self.__y_data)) ** 2)

    def Adjust_R2(self):
        """

        :return: Adjust R2 of the result
        """
        return 1 - (1 - self.R2()) * (self.__n - 1) / (self.__n - self.__k - 1)

    def RMSE(self):
        """

        :return: RMSE of the result
        """
        return torch.sqrt(torch.sum(self.__residual ** 2) / self.__n)

class Visualize():

    def __init__(self,data,lon_lat_columns = None,zoom = 4):
        self.__raw_data = data
        self.__tiles= 'https://wprd01.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=en&size=1&scl=1&style=7'
        self.__zoom = zoom
        if (hasattr(self.__raw_data,'_use_gpu')):
            self._train_dataset = self.__raw_data._train_dataset.dataframe
            self._valid_dataset = self.__raw_data._valid_dataset.dataframe
            self._test_dataset = self.__raw_data._test_dataset.dataframe
            self._result_data = self.__raw_data.result_data
            self._all_data = pd.concat([self._train_dataset,self._valid_dataset,self._test_dataset])
            if lon_lat_columns == None:
                warnings.warn("lon_lat columns are not given. Using the spatial columns in dataset")
                self._spatial_column = self._train_dataset.spatial_column
                self.__center_lon = self._all_data[self._spatial_column[0]].mean()
                self.__center_lat = self._all_data[self._spatial_column[1]].mean()
                self.__lon_column = self._spatial_column[0]
                self.__lat_column = self._spatial_column[1]
            else :
                self._spatial_column = lon_lat_columns
                self.__center_lon = self._all_data[self._spatial_column[0]].mean()
                self.__center_lat = self._all_data[self._spatial_column[1]].mean()
                self.__lon_column = self._spatial_column[0]
                self.__lat_column = self._spatial_column[1]
            self._x_column = data._train_dataset.x_column
            self._y_column = data._train_dataset.y_column
            self.__map = folium.Map(location=[self.__center_lat,self.__center_lon],zoom_start=zoom,tiles = self.__tiles,attr="高德")
        else:
            raise ValueError("given data is not instance of GNNWR")
    
    def display_dataset(self,name="all",y_column=None,steps=20):
        # colormap = branca.colormap.linear.RdYlGn_10.scale().to_step(steps)
        if y_column == None:
            warnings.warn("y_column is not given. Using the first y_column in dataset")
            y_column = self._y_column[0]
        if name == 'all':
            dst = self._all_data
        elif name == 'train':
            dst = self._train_dataset
        elif name == 'valid':
            dst = self._valid_dataset
        elif name == 'test':
            dst = self._test_dataset
        else:
            raise ValueError("name is not included in 'all','train','valid','test'")
        dst_min = dst[y_column].min()
        dst_max = dst[y_column].max()
        res = folium.Map(location=[self.__center_lat,self.__center_lon],zoom_start=self.__zoom,tiles = self.__tiles,attr="高德")
        colormap = branca.colormap.linear.YlOrRd_09.scale(dst_min,dst_max).to_step(20)
        for idx,row in dst.iterrows():
            folium.CircleMarker(location=[row[self.__lat_column],row[self.__lon_column]],radius=7,color=colormap.rgb_hex_str(row[y_column]),fill=True,fill_opacity=1,
            popup="""
            longitude:{}
            latitude:{}
            {}:{}
            """.format(row[self.__lon_column],row[self.__lat_column],y_column,row[y_column])
            ).add_to(res)
        res.add_child(colormap)
        return res

    def weights_heatmap(self,data_column):
        res = folium.Map(location=[self.__center_lat,self.__center_lon],zoom_start=self.__zoom,tiles = self.__tiles,attr="高德")
        dst = self._result_data
        data = [[row[self.__lat_column],row[self.__lon_column],row[data_column]]for index,row in dst.iterrows()]
        colormap = branca.colormap.linear.YlOrRd_09.scale(dst[data_column].min(),dst[data_column].max()).to_step(20)
        gradient_map = dict()
        for i in range(20):
            gradient_map[i/20] = colormap.rgb_hex_str(i/20)
        colormap.add_to(res)
        HeatMap(data=data,gradient=gradient_map,radius=10).add_to(res)
        return res
    