import argparse
import os
import os.path as osp
import random
from uuid import uuid4

import albumentations as A
import numpy as np
from colorama import Fore
from nanoid import generate

import utils

r"""
    ===================000000000000
    ===================000000000000
    ===================000000000000
    $$$$$$$$$$$$$$$$$$$xxxxxxxxxxxx
    $$$$$$$$$$$$$$$$$$$xxxxxxxxxxxx
    $$$$$$$$$$$$$$$$$$$xxxxxxxxxxxx
    $$$$$$$$$$$$$$$$$$$xxxxxxxxxxxx

    ===== Top left image: [0: div_point_y, 0: div_point_x, :]       (width height) = (div_point_x, div_point_y)
    00000 Top right image: [0: div_point_y, div_point_x:, :]        (width, height) = (width - div_point_x, div_point_y)
    $$$$$ Bottom left image: [div_point_y:, 0: div_point_x, :]      (width, height) = (div_point_x, height - div_point_y)
    xxxxx Bottom right image: [div_point_y:, div_point_x:, :]       (width, height) = (width - div_point_x, height - div_point_y)
"""

# Random crop image with predefined size and save coordinates of boxes
def random_crop_savebboxes(image_name:str, image_dir:str, label_dir:str, 
                           expected_h:int, expected_w:int, 
                           min_area:int, min_visibility:float) -> tuple:
    r"""
        Implement random crop image
        >>> image_name:     for example img_0.jpg
        >>> image_dir:      original image directory
        >>> label_dir:      orrigianl label directory
        >>> expected_h:     expected height of the image, it depends on the scale_y
        >>> expected_w:     expected width of the image, it depends on the scale_x
        >>> min_area:       threshol of area of bounding boxes. If area of box after augmentation < min_area, we will drop that box.
        >>> min_visibility: [0, 1]  If the ratio of the box area after augmentation to the area of the box before augmentation 
                                becomes smaller than min_visibility, we will drop that box.
    """
    image_path, label_path, _ =  utils.preprocess(image_name, image_dir, label_dir)

    bboxes, class_labels = utils.read_label(label_path)

    transform = A.Compose([A.RandomResizedCrop(expected_h, expected_w)],     
                           bbox_params=A.BboxParams(
                               format='yolo', label_fields=['class_labels'], 
                               min_area=min_area, min_visibility=min_visibility))   # height, width

    transformed = transform(image=utils.read_img(image_path), 
                            bboxes=bboxes, class_labels=class_labels)
    transformed_image = transformed['image']
    transformed_bboxes = transformed['bboxes']
    transformed_class_labels = transformed['class_labels']  # list

    return transformed_image, transformed_bboxes, transformed_class_labels


def create_data_store_path(output_image_dir:str, output_label_dir:str, 
                     image_file_list:list) -> tuple: 
    
    image_store_path = osp.sep.join([output_image_dir, 'mo_' + \
                                image_file_list[0].split('.')[0] + '_' + \
                                image_file_list[1].split('.')[0] + '_' + \
                                image_file_list[2].split('.')[0] + '_' + \
                                image_file_list[3].split('.')[0] + '.jpg'])
    
    label_store_path = osp.sep.join([output_label_dir, 'mo_' + \
                                    image_file_list[0].split('.')[0] + '_' + \
                                    image_file_list[1].split('.')[0] + '_' + \
                                    image_file_list[2].split('.')[0] + '_' + \
                                    image_file_list[3].split('.')[0] + '.txt'])
    
    return image_store_path, label_store_path


def mosaic(image_file_list:list, image_dir:str, label_dir:str, 
           output_image_dir:str, output_label_dir:str, 
           mo_w:int, mo_h:int, scale_x:float, scale_y:float, 
           min_area:int, min_visibility:float,
           display:bool=False) -> None:
    r"""
        Implement mosaic augmentation
        >>> image_file_list:    list of 4 images (only name of image, not path), [img_1.jpg, img_2.jpg, img_3.png, img_4.jpeg]
        >>> image_dir:          original image directory
        >>> label_dir:          orrigianl label directory
        >>> output_image_dir:   path of directory for mosaic images
        >>> output_label_dir:   path of directory for new labels
        >>> mo_h:               height of mosaic-augmented image
        >>> mo_w:               width of mosaic-augmented image
        >>> min_area:           threshol of area of bounding boxes. If area of box after augmentation < min_area, we will drop that box.
        >>> min_visibility:     [0, 1]  If the ratio of the box area after augmentation to the area of the box before augmentation 
                                    becomes smaller than min_visibility, we will drop that box.
    """
    # creat a new image
    new_img = np.empty((mo_h, mo_w, 3), dtype='uint8')     # 3 channels

    # split points
    div_point_x = int(mo_w * scale_x)
    div_point_y = int(mo_h * scale_y)

    # loop through images
    for i in range(4): # for i in range(len(image_file_list)):
        if not i: # i == 0 || top left image, img_0
            # width and height of the top left image
            w0 = div_point_x
            h0 = div_point_y
            img_0, bboxes_0, class_labels_0 = random_crop_savebboxes(
                image_file_list[0], image_dir, label_dir, h0, w0, min_area, min_visibility)
            # top left
            new_img[:div_point_y, :div_point_x, :] = img_0 

            # change parameters of bboxes for the top left image, chú ý bboxes ở dạng list of tuple mà tuple ko cho gán nên ta tạo list mới
            if len(bboxes_0) == 0:  # there is no boxes
                bboxes_0_new = []
            else:
                # !!! Don't create nested list as follow: bboxes_0_new = [[None, None, None, None]] * len(bboxes_0)
                # because inner lists have the same id => incorrect result when perform operations.

                # nested list for bboxes
                bboxes_0_new = np.zeros((len(bboxes_0), 4))
                # convert to list
                bboxes_0_new = bboxes_0_new.tolist()

            for i, box in enumerate(bboxes_0):
                bboxes_0_new[i][0] = box[0] * scale_x   # xcenter
                bboxes_0_new[i][2] = box[2] * scale_x   # w

                bboxes_0_new[i][1] = box[1] * scale_y   # ycenter
                bboxes_0_new[i][3] = box[3] * scale_y   # h
                
        elif i == 1: # top right image
            w1 = mo_w - div_point_x     # trừ sẽ khớp
            h1 = div_point_y    # giữ nguyên như cái i=0
            img_1, bboxes_1, class_labels_1 = random_crop_savebboxes(
                image_file_list[1], image_dir, label_dir, h1, w1, min_area, min_visibility)
            new_img[:div_point_y, div_point_x:, :] = img_1

            # change bboxes
            if len(bboxes_1) == 0:  # TH không có bboxes nào
                bboxes_1_new = []
            else:
                bboxes_1_new = np.zeros((len(bboxes_1), 4))
                # convert to list
                bboxes_1_new = bboxes_1_new.tolist()

            for i, box in enumerate(bboxes_1):
                bboxes_1_new[i][0] = box[0] * (1 - scale_x) + scale_x   # xcenter
                bboxes_1_new[i][2] = box[2] * (1 - scale_x)             # w

                bboxes_1_new[i][1] = box[1] * scale_y       # ycenter
                bboxes_1_new[i][3] = box[3] * scale_y       # h
        
        elif i == 2: # bottom left image
            w2 = div_point_x
            h2 = mo_h - div_point_y
            img_2, bboxes_2, class_labels_2 = random_crop_savebboxes(
                image_file_list[2], image_dir, label_dir, h2, w2, min_area, min_visibility)
            new_img[div_point_y:, :div_point_x, :] = img_2

            # change bboxes
            if len(bboxes_2) == 0:  # there is no boxes
                bboxes_2_new = []
            else:
                bboxes_2_new = np.zeros((len(bboxes_2), 4))
                # convert to list
                bboxes_2_new = bboxes_2_new.tolist()

            for i, box in enumerate(bboxes_2):
                bboxes_2_new[i][0] = box[0] * scale_x       # xcenter
                bboxes_2_new[i][2] = box[2] * scale_x       # w

                bboxes_2_new[i][1] = box[1] * (1 - scale_y) + scale_y       # ycenter
                bboxes_2_new[i][3] = box[3] * (1 - scale_y)                 # h

        else: # bottom right image
            w3 = mo_w - div_point_x
            h3 = mo_h - div_point_y
            img_3, bboxes_3, class_labels_3 = random_crop_savebboxes(
                image_file_list[3], image_dir, label_dir, h3, w3, min_area, min_visibility)
            new_img[div_point_y:, div_point_x:, :] = img_3 

            # change bboxes
            if len(bboxes_3) == 0:  # there is no boxes
                bboxes_3_new = []
            else:
                bboxes_3_new = np.zeros((len(bboxes_3), 4))
                # convert to list
                bboxes_3_new = bboxes_3_new.tolist()

            for i, box in enumerate(bboxes_3):
                bboxes_3_new[i][0] = box[0] * (1 - scale_x) + scale_x       # xcenter
                bboxes_3_new[i][2] = box[2] * (1 - scale_x)                 # w

                bboxes_3_new[i][1] = box[1] * (1 - scale_y) + scale_y       # ycenter
                bboxes_3_new[i][3] = box[3] * (1 - scale_y)                 # h

    # all classes in the augmented image
    new_class_labels = class_labels_0 + class_labels_1 + class_labels_2 + class_labels_3
    # all bounding boxex in the augmented image
    new_bboxes = bboxes_0_new + bboxes_1_new + bboxes_2_new + bboxes_3_new

    # path to save image and label
    image_store_path, label_store_path = create_data_store_path(
        output_image_dir, output_label_dir, image_file_list)
    
    # save the augmented image and labels (bounding boxes)
    utils.save_img(new_img, image_store_path )
    utils.save_label(new_bboxes, new_class_labels, label_store_path)

    r""" If you want to see the augmented with their bounding boxes, if not please COMMENT row below """
    if display: utils.display_img(image_store_path, label_store_path)


def create_args():
    ap = argparse.ArgumentParser(description="Mosiac image augumentation with yolo annotation")
    ap.add_argument("--ip_dir", required=True, type=str, help="input folder contain both image and yolo annotation")
    ap.add_argument("--op_dir", required=True, type=str, help="output folder contain both image and yolo annotation")
    ap.add_argument("--width", default=800, required=True, type=int, help="width of mosaic-augmented image")
    ap.add_argument("--height", default=800, required=True, type=int, help="height of mosaic-augmented image")
    
    # scale by width and height => we can define size of each image
    ap.add_argument("--scale_x", default=0.4, required=True, type=float, help="scale_x - scale by width => define width of the top left image")
    ap.add_argument("--scale_y", default=0.6, required=True, type=float, help="scale_y - scale by height => define height of the top left image")
    ap.add_argument("--min_area", default=200, required=True, type=int, help="min area of box after augmentation we will keep. If area of box < min_area we will drop the box")
    ap.add_argument("--min_vi", default=0.1, required=True, type=float, help="min area ratio of box after/before augmentation we will keep")
    
    return ap.parse_args()


if __name__ == "__main__":
    args = create_args()
    # create folder to store augmented images and correspond labels
    if not osp.exists(args.op_dir): os.makedirs(args.op_dir)

    r"""
        Note: Image and label must have the same name.
        For example: image_1.jpeg - image_1.txt
    """
    print('Processing...')

    # get a list of all images
    pics = [img for img in os.listdir(args.ip_dir) 
            if img.endswith('.jpg') or img.endswith('.jpeg') or img.endswith('.png')]
    # randomly get 4 images
    image_file_list = random.choices(pics, k=4)
    # perform augmentation
    mosaic(image_file_list, 
           args.ip_dir, args.ip_dir, 
           args.op_dir, args.op_dir, 
           args.width, args.height, 
           args.scale_x, args.scale_y, 
           args.min_area, args.min_vi, False)
