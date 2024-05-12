__copyright__   = "Copyright 2024, VISA Lab"
__license__     = "MIT"

import os
import csv
import sys
import torch
from PIL import Image
from Resources.model.facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import datasets
from torch.utils.data import DataLoader

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion
# test_image = sys.argv[1]
# data_path = sys.argv[2]

def face_match(input_img, data_path='data.pt'): # img_path= location of photo, data_path= location of data.pt, input_img = passing actual photo instead of path
    # getting embedding matrix of the given img
    img = Image.open(input_img)
    face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false

    saved_data = torch.load(data_path) # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person

    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))

# result = face_match(test_image, data_path='./Resources/model/data.pt')
# print(result[0])

if __name__ == "__main__":
    test_image = sys.argv[1]
    data_path = sys.argv[2]
    result = face_match(test_image, data_path)
    print(result[0])