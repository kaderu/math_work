# -*- coding: UTF-8 -*-
# @Time : 2024/3/19 17:38
# @File : pixel_distribute.py
# @Author: zhangshangzhi
# @Description:
import re
from statistics import mean

import pandas as pd
import numpy as np

from backend.base.base import OcrCell, Page_Structure


class ModeTrigger:

    def __init__(self, hit_keys):
        self._hit_keys = hit_keys

    def shall_we_start(self, text):
        if text is None:
            return False
        if len(self._hit_keys) > 0:
            temp_hit_keys = [k for k in self._hit_keys if k in text]
            self._hit_keys = list(set(self._hit_keys) - set(temp_hit_keys))
        if len(self._hit_keys) == 0:
            return True
        return False


class CommonTrigger:

    static_choose_hit_keys = ['选择题', '共10小题', '每小题3分']
    static_fill_in_hit_keys = ['填空题', '共6小题', '每小题3分']
    static_solve_hit_keys = ['解答题', '共8小题']

    def __init__(self):
        self.instance_dic = {
            'choose': ModeTrigger(self.static_choose_hit_keys),
            'fill_in': ModeTrigger(self.static_fill_in_hit_keys),
            'solve': ModeTrigger(self.static_solve_hit_keys)
        }

    @staticmethod
    def static_number_2_mode(aim_number):
        if aim_number <= 10:
            return 'choose'
        elif aim_number <= 16:
            return 'fill_in'
        else:
            return 'solve'

    def aim(self, aim_number):
        mode = self.static_number_2_mode(aim_number)
        return self.instance_dic[mode]


class PixelCube:

    def __init__(self, pieces_input, trigger, number_operator=0):
        self.ocr_pieces = [OcrCell(piece) for piece in pieces_input]
        # 识别题号并标识
        self.numbers = self.decorate(trigger, number_operator)

    def distribute(self):

        # 分布范围框定
        pieces = self.ocr_pieces

        # 数据准备
        p_starts = np.array([piece.coordinate[0][0] for piece in pieces])
        p_ends = np.array([piece.coordinate[1][0] for piece in pieces])
        p_heights = np.array([piece.coordinate[2][1] - piece.coordinate[0][1]for piece in pieces])
        p_text_lens = np.array([len(piece.text) for piece in pieces])

        # 计算单个字符的像素宽度、高度
        char_width = mean((p_ends - p_starts) / p_text_lens)
        char_height = mean(p_heights)

        # 计算左版边
        p_starts_bar = p_starts // char_width * char_width
        left_edge = pd.value_counts(p_starts_bar).sort_values(ascending=False).index[0]

        # 计算题号左版边
        p_number_starts = np.array([piece.coordinate[0][0] for piece in pieces if piece.number is not None])
        p_number_starts_bar = p_number_starts // char_width * char_width
        number_left_edge = pd.value_counts(p_number_starts_bar).sort_values(ascending=False).index[0]

        # 计算右版边
        p_middle = mean([(pe + ps)/2 for pe, ps in zip(p_ends, p_starts) if ps >= left_edge])
        p_ends_bar = (p_ends // char_width + 1) * char_width
        # p_ends_bar = [pe for pe in p_ends_bar if pe > 2 * p_middle - left_edge]
        p_ends_bar = [pe for pe in p_ends_bar if pe > p_middle]
        right_edge = pd.value_counts(p_ends_bar).sort_values(ascending=False).index[0]

        # 计算下版边 base on 试卷第4页（共6页）
        bottom_edge = self.ocr_pieces[-1].coordinate[2][1]
        pattern = r'.*第[0-9]页.*共[0-9]页'
        for ocr_piece in self.ocr_pieces[::-1]:
            if re.match(pattern, ocr_piece.text):
                ocr_piece.is_footer = True
                bottom_edge = ocr_piece.coordinate[0][1] - 26
                break

        # 返回
        page_structure = Page_Structure(
            left_edge=left_edge,
            right_edge=right_edge,
            middle_pixel=p_middle,
            char_width=char_width,
            char_height=char_height,
            numbers=self.numbers,
            number_left_edge=number_left_edge,
            ocr_cells=self.ocr_pieces,
            bottom_edge=bottom_edge
        )
        return page_structure

    def decorate(self, trigger, number_operator=0):

        numbers = []

        for i, ocr_piece in enumerate(self.ocr_pieces):

            aim_number = number_operator + len(numbers) + 1

            start = trigger.aim(aim_number).shall_we_start(ocr_piece.text)
            if not start:
                continue

            pattern = r"^{}\.".format(aim_number)
            if re.search(pattern, ocr_piece.text):
                # 题目编号
                ocr_piece.number = aim_number
                numbers.append(aim_number)
            # 回环校验 不使用

        return numbers


class MiniPixelCube:

    def __init__(self, pieces_input, mode='fill_in'):
        self.ocr_pieces = [OcrCell(piece) for piece in pieces_input]
        if mode == 'fill_in':
            self.keys = ['二、填空题', '非选择题']
        elif mode == 'solve':
            self.keys = ['三、解答题']
        else:
            self.keys = ['一、选择题']

    def get_height(self):
        for i, ocr_piece in enumerate(self.ocr_pieces):
            text = ocr_piece.text
            if any([key in text for key in self.keys]):
                return i, ocr_piece.coordinate[0][1]
        return 0, None

