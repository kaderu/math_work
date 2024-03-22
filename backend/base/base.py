# -*- coding: UTF-8 -*-
# @Time : 2024/3/18 16:29
# @File : base.py
# @Author: zhangshangzhi
# @Description:
import os
from dataclasses import dataclass


@dataclass
class OcrCell:
    # 格式：[[86.0, 111.0], [191.0, 111.0], [191.0, 132.0], [86.0, 132.0]]
    coordinate: list
    # OCR文字
    text: str
    # 置信度
    confidence: float

    def __init__(self, piece_input):
        self.coordinate = piece_input[0]
        self.text = piece_input[1][0].strip()
        self.confidence = piece_input[1][1]
        self.number = None
        self.is_header = False
        self.is_footer = False
        # self.useless = False

    def type(self):
        if self.number is None:
            return None
        elif self.number <= 10:
            return 'choose'
        elif self.number <= 16:
            return 'fill_in'
        else:
            return 'solve'


@dataclass
class MetaCell:
    # 格式：[[86.0, 111.0], [191.0, 111.0], [191.0, 132.0], [86.0, 132.0]]
    coordinate: list
    # OCR文字
    texts: list

    def __init__(self, oc):
        self.coordinate = oc.coordinate
        self.texts = [oc.text]

    def integrate(self, oc):
        self.coordinate = [
            self._merge(self.coordinate[0], oc.coordinate[0], 2),
            self._merge(self.coordinate[1], oc.coordinate[1], 1),
            self._merge(self.coordinate[2], oc.coordinate[2], 4),
            self._merge(self.coordinate[3], oc.coordinate[3], 3)
        ]
        self.texts.append(oc.text)

    @staticmethod
    def _merge(self, p1, p2, quadrant=2):
        """
        :param p1: 点1坐标
        :param p2: 点2坐标
        :param quadrant: 象限，1-4，1为第一象限，2为第二象限，以此类推
        :return:
        """
        if quadrant == 1:
            method1 = max
            method2 = min
        if quadrant == 2:
            method1 = min
            method2 = min
        if quadrant == 3:
            method1 = min
            method2 = max
        if quadrant == 4:
            method1 = max
            method2 = max
        return [method1(p1[0], p2[0]), method2(p1[1], p2[1])]


@dataclass
class CutCell:
    # 左上、右下，格式：[[86.0, 111.0], [191.0, 132.0]]
    coordinate: list
    # OCR文字
    texts: list

    def __init__(self, coordinate, path=None):
        self.coordinate = coordinate
        self.path = path
        self.texts = []

    def delete(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def get_number(self):
        number_str = self.path.split('_')[-1].split('.')[0]
        return int(number_str)



@dataclass
class Page_Structure:
    # 左边缘
    left_edge: float
    # 右边缘
    right_edge: float
    # 中心像素（行）
    middle_pixel: float
    # 字符宽
    char_width: float
    # 字符高
    char_height: float
    # 题号
    numbers: list
    # 题号左边缘
    number_left_edge: float
    # 页码
    page_num: int = None
    # 上边缘 TODO 漏图处理
    head_edge: float = None
    # 下边缘
    bottom_edge: float = None
    # ocr_cells
    ocr_cells: list = None
    # img_path
    img_path: str = None
