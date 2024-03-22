# -*- coding: UTF-8 -*-
# @Time : 2024/3/20 11:33
# @File : ocr_domain.py
# @Author: zhangshangzhi
# @Description:
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from backend.base.base import CutCell
from backend.nlp.pixel_distribute import PixelCube, CommonTrigger, MiniPixelCube


class OcrDomain:

    def __init__(self, path):
        self.path = path
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        self.number_operator = 0
        self.trigger = CommonTrigger()

    def _page_cutter(self, buffer=100):

        img = Image.open(self.path)
        width, height = img.size

        page = 0
        save_path_format = self.path.replace('.jpg', '_p{}.jpg')
        page_imgs = []

        while page * width * 99/70 < height - buffer: # A4纸长宽比=99/70
            head = page * width * 99/70
            bottom = (page + 1) * width * 99/70
            page += 1
            page_img = save_path_format.format(page)
            self._img_cut(img, (0, head), (width, bottom), page_img, tab_space=0, line_space=0)
            page_imgs.append(page_img)

        return page_imgs

    def _in_page_ocr(self, page_path):
        """
        页内OCR识别
        :param page_path:
        :return:
        """

        # OCR识别
        result = self.ocr.ocr(page_path, cls=True)
        result = result[0]

        # 分析页面结构
        pixel_cube = PixelCube(result, self.trigger, self.number_operator)
        page_structure = pixel_cube.distribute()

        # 更新题号算子
        self.number_operator += len(page_structure.numbers)
        # print(page_path, page_structure)

        return page_structure

    def _global_cell_cut(self, page_structures, img_paths):
        """
        全局切割
        :param page_structures: 页面OCR结构体
        :param img_paths: 页面图路径
        :return:
        """

        cut_cells_list = []

        for p_s, img_path in zip(page_structures, img_paths):

            # 页面图
            img = Image.open(img_path)

            # 计算各个题目对应的左上、右下角坐标
            number_ocr_cells = [o_c for o_c in p_s.ocr_cells if o_c.number is not None]
            coords_1 = [(p_s.number_left_edge, cell.coordinate[0][1]) for cell in number_ocr_cells]
            coords_2 = [(p_s.right_edge, max(cell.coordinate[0][1] - p_s.char_height, 0)) for cell in number_ocr_cells]
            coords_1.insert(0, (p_s.number_left_edge, 0))
            coords_2.append((p_s.right_edge, p_s.bottom_edge))

            # 保存地址
            save_path_format = img_path.replace('source', 'source/output').replace('.jpg', '_{}.jpg')
            save_paths = [save_path_format.format(i) for i in p_s.numbers]
            save_paths.insert(0, save_path_format.format('hb'))  # head_buffer

            # 遍历cell，完成图片切割和cut_cell初始化
            cut_cells = []
            for coords_1, coords_2, save_path in zip(coords_1, coords_2, save_paths):
                self._img_cut(img, coords_1, coords_2, save_path, tab_space=50, line_space=26)
                cut_cell = CutCell([coords_1, coords_2], save_path)
                cut_cells.append(cut_cell)

            # cut_cell的ocr信息完善
            # 过滤超过页面结构的ocr
            o_cs = [o_c for o_c in p_s.ocr_cells
                    if o_c.coordinate[0][0] >= p_s.number_left_edge
                    and o_c.coordinate[1][0] <= p_s.right_edge]
            # 过滤页眉页脚
            o_cs = [o_c for o_c in o_cs if not o_c.is_header and not o_c.is_footer]
            # 制作切片，将切片内的text放入对应的cut_cell
            idx = [i for i, o_c in enumerate(o_cs) if o_c.number is not None]
            idx.insert(0, 0)
            idx.append(len(o_cs))
            for c_e, a, b in zip(cut_cells, idx[:-1], idx[1:]):
                c_e.texts.extend([oc.text for oc in o_cs[a:b]])

            cut_cells_list.append(cut_cells)

        return cut_cells_list

    @staticmethod
    def _img_cut(img, coord1, coord2, save_path, tab_space=0, line_space=0):
        """
        切割图片
        :param img:
        :param coord1: 左上坐标
        :param coord2: 右下坐标
        :param save_path: 保存路径
        :param tab_space: 左右页边距
        :param line_space: 上下页边距
        :return:
        """

        # 创建一个新的空白图片
        cut_img = Image.new('RGB', (
            int(coord2[0] - coord1[0]) + tab_space
            , int(coord2[1] - coord1[1]) + line_space)
                            , 'white'
                            )

        # 裁剪题目，粘贴到新图上
        cut_img.paste(
            img.crop(
                (max(coord1[0] - tab_space / 2, 0), max(coord1[1] - line_space / 2, 0),
                 coord2[0] + tab_space / 2, coord2[1] + line_space / 2)),
            # (tab_space, line_space)
            (0, 0)
        )

        # 保存图片
        cut_img.save(save_path)

    def _global_img_crop(self, cut_cells_list):
        """
        全局图片去空白
        :param cut_cells_list:
        :return:
        """

        for cut_cells in cut_cells_list:
            for c_e in cut_cells:
                self._img_crop(c_e.path)

    @staticmethod
    def _img_crop(img_path):
        """
        图片去空白
        :param img_path:
        :return:
        """

        img = Image.open(img_path)
        img_array = np.array(img)
        row, col = img_array.shape[0], img_array.shape[1]

        x_left, x_top, x_right, x_bottom = row, col, 0, 0
        for r in range(row):
            for c in range(col):
                if img_array[r][c][0] < 255 and img_array[r][c][0] != 0:  # 外框有个黑色边框，增加条件判断
                    if x_top > r:
                        x_top = r  # 获取最小x_top
                    if x_bottom < r:
                        x_bottom = r  # 获取最大x_bottom
                    if x_left > c:
                        x_left = c  # 获取最小x_left
                    if x_right < c:
                        x_right = c  # 获取最大x_right
        # print(x_left, x_top, x_right, x_bottom)

        cut_img = Image.new('RGB', (x_right - x_left + 10, x_bottom - x_top + 10), 'white')
        cut_img.paste(img.crop((x_left, x_top, x_right, x_bottom)), (5, 5))
        cut_img.save(img_path)

    def _global_cell_concat(self, cut_cells_list):
        """
        全局合并
        :param cut_cells_list: 嵌套list，按page收集了cut_cells
        :return:
        """

        # 上一个待合并的cell
        buffer_cell = None

        # 遍历page，完成buffer_cell与head_cell的合并
        for i, cut_cells in enumerate(cut_cells_list):
            if buffer_cell is not None:
                self._cell_concat(buffer_cell, cut_cells[0])
            # 移除head_cell并删除图片
            cut_cells.pop(0).delete()
            buffer_cell = cut_cells[-1]

    def _description_remove(self, cut_cells_list):
        """
        去除题型描述
        :param cut_cells_list: 嵌套list，按page收集了cut_cells
        :return:
        """

        for cut_cells in cut_cells_list:
            for cut_cell in cut_cells:

                mode = None
                if cut_cell.get_number() == 10:
                    mode = 'fill_in'
                elif cut_cell.get_number() == 16:
                    mode = 'solve'
                if mode is None:
                    continue

                # OCR识别
                result = self.ocr.ocr(cut_cell.path, cls=True)
                result = result[0]

                # 分析页面结构
                mini_pixel_cube = MiniPixelCube(result, mode)
                idx, height = mini_pixel_cube.get_height()

                # 图片切割
                if height is not None:
                    print(idx, height)
                    img = Image.open(cut_cell.path)
                    self._img_cut(
                        img, (0, 0), (img.size[0], height),
                        cut_cell.path)
                    cut_cell.texts = cut_cell.texts[:idx]

    def _cell_concat(self, cell1, cell2):
        """
        将cell2合并到cell1中
        :param cell1:
        :param cell2:
        :return: None
        """

        cell1.texts.extend(cell2.texts)
        self._img_concat(cell1.path, cell2.path)

    def _img_concat(self, path1, path2, tab_space=50, line_space=26):
        """
        合并两张图片
        :param path1:
        :param path2:
        :param tab_space:
        :param line_space:
        :return:
        """

        img1 = Image.open(path1)
        img2 = Image.open(path2)
        merge_img = Image.new('RGB',
                              (max(img1.size[0], img2.size[0]) + tab_space,
                               img1.size[1] + img2.size[1] + line_space)
                              , 'white'
                              )
        merge_img.paste(img1, (0, 0))
        merge_img.paste(img2, (0, img1.size[1]))
        merge_img.save(path1)

    def process(self):
        """
        处理流程
        :return: cut_cell集合
        """

        # 分页切割
        paths = self._page_cutter()

        # OCR及分析
        page_structures = [self._in_page_ocr(path) for path in paths]

        # 单元切割
        cut_cells_list = self._global_cell_cut(page_structures, paths)

        # 单元合并
        self._global_cell_concat(cut_cells_list)

        # 题型描述移除
        self._description_remove(cut_cells_list)

        # 配图归属
        # TODO

        # 图片去空白
        self._global_img_crop(cut_cells_list)

        return cut_cells_list


if __name__ == '__main__':
    ocr = OcrDomain('source/640.jpg')
    result = ocr.process()
    print(result)
