# -*-coding:utf-8-*-
import base64
import contextlib
import io
import json
import os.path as osp

import PIL.Image
import utils
from enum import Enum
PIL.Image.MAX_IMAGE_PIXELS = None
from widgets import __TXT_SUFFIX__



@contextlib.contextmanager
def open(name, mode):
    assert mode in ["r", "w"]
    encoding = "utf-8"
    yield io.open(name, mode, encoding=encoding)
    return


class LabelFileError(Exception):
    pass

class LabelFileFormat(Enum):
    JSON = 1
    CULANE = 2


class LabelFile(object):
    json_suffix = ".json"
    def __init__(self, filename=None,img_suffix = None,txt_suffix = None):

        self.shapes = []
        self.imagePath = None
        self.imageData = None
        if filename is not None:
            suffix = osp.splitext(filename)[-1]
            if suffix == ".json":
                self.load(filename)
            else:
                self.loadtxt(filename,img_suffix)
        self.filename = filename

    @staticmethod
    def load_image_file(filename):
        try:
            image_pil = PIL.Image.open(filename)
        except IOError:
            return

        # 根据图像的exif调整方向
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()

            if ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()
    def loadtxt(self,filename,img_suffix):

        # 没有图片数据的话就得到图片的绝对路径
        imagePath = osp.join(osp.dirname(filename),img_suffix)
        imageData = self.load_image_file(imagePath)
        flags = {}
        imagePath = img_suffix

        point_list = []
        points1 = []
        self.shapes = []
        count = 0
        with open(filename, "r") as f:
            for data in f.readlines():
                data = data.strip('\n')
                data = data.split()
                for i, points in enumerate(data):
                    points1.append(points)
                    if (i + 1) % 2 == 0:
                        point_list.append(points1)
                        points1 = []
                count+=1
                shape=dict(
                    label=str(count),
                    points=point_list,
                    shape_type="linestrip",
                    flags={},
                    group_id=None,
                    other_data={},
                )
                self.shapes.append(shape)
                point_list = []


        self.flags = flags
        #self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename


    def load(self, filename):
        keys = [
            "imageData",
            "imagePath",
            "shapes",  # polygonal annotations
            "flags",  # image level flags
            "imageHeight",
            "imageWidth",
        ]
        shape_keys = [
            "label",
            "points",
            "group_id",
            "shape_type",
            "flags",
        ]
        try:
            with open(filename, "r") as f:
                data = json.load(f)

            if data["imageData"] is not None:
                imageData = base64.b64decode(data["imageData"])
            else:
                #没有图片数据的话就得到图片的绝对路径
                imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                imageData = self.load_image_file(imagePath)
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            self._check_image_height_and_width(
                base64.b64encode(imageData).decode("utf-8"),
                data.get("imageHeight"),
                data.get("imageWidth"),
            )
            shapes = [
                dict(
                    label=s["label"],
                    points=s["points"],
                    shape_type=s.get("shape_type", "polygon"),
                    flags=s.get("flags", {}),
                    group_id=s.get("group_id"),
                    other_data={
                        k: v for k, v in s.items() if k not in shape_keys
                    },
                )
                for s in data["shapes"]
            ]
        except Exception as e:
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # 只在所有内容加载后替换数据。
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        img_arr = utils.img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            print(
                "imageHeight does not match with imageData or imagePath, "
                "so getting imageHeight from actual image."
            )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            print(
                "imageWidth does not match with imageData or imagePath, "
                "so getting imageWidth from actual image."
            )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    def save(
            self,
            filename,
            shapes,
            imagePath,
            imageHeight,
            imageWidth,
            imageData=None,
            otherData=None,
            flags=None,
            label_file_format = None,
    ):
        # if imageData is not None:
        #     imageData = base64.b64encode(imageData).decode("utf-8")
        #     imageHeight, imageWidth = self._check_image_height_and_width(
        #         imageData, imageHeight, imageWidth
        #     )
        if label_file_format == LabelFileFormat.JSON:
            if otherData is None:
                otherData = {}
            if flags is None:
                flags = {}
            data = dict(
                flags=flags,
                shapes=shapes,
                imagePath=imagePath,
                imageData=imageData,
                imageHeight=imageHeight,
                imageWidth=imageWidth,
            )
            for key, value in otherData.items():
                assert key not in data
                data[key] = value
            try:
                with open(filename, "w") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.filename = filename
            except Exception as e:
                raise LabelFileError(e)
        elif label_file_format == LabelFileFormat.CULANE:
            #filename = osp.splitext(filename)[0]
            pList = []
            with open(filename, 'w') as ftxt:
                for points_list in shapes:
                    for points in points_list["points"]:
                        for point in points:
                            pList.append(point)
                    for point in pList:
                        ftxt.write(str(round(point, 4)) + " ")#

                    ftxt.write("\n")
                    pList.clear()
        else:
            raise ValueError('无法保存该格式文件')
    @staticmethod
    def is_label_file(filename,TXT_SUFFIX):
        return osp.splitext(filename)[1].lower() == LabelFile.json_suffix or \
        osp.splitext(filename)[1].lower()== osp.splitext(TXT_SUFFIX)[-1]
