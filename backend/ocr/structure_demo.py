# -*- coding: UTF-8 -*-
# @Time : 2024/3/15 16:50
# @File : structure_demo.py
# @Author: zhangshangzhi
# @Description:


import os
import cv2
from paddleocr import PPStructure,save_structure_res

table_engine = PPStructure(table=False, ocr=False, show_log=True)

save_folder = 'source/output'
img_path = 'source/640_p3.jpg'
img_path = 'source/640.jpg'
img = cv2.imread(img_path)
result = table_engine(img)
save_structure_res(result, save_folder, os.path.basename(img_path).split('.')[0])

for line in result:
    line.pop('img')
    print(line)