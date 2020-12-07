from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model

import numpy as np
import argparse
import cv2
import os

import argparse
import random
import os

from PIL import Image
from tqdm import tqdm


SIZE = 64

parser = argparse.ArgumentParser()
parser.add_argument('--data-dir', default='data/dataset_raw', help="Directory with the SIGNS dataset")
parser.add_argument('--output-dir', default='data/64x64_dataset', help="Where to write the new data")
parser.add_argument("--face", type=str, default="face_detector", help="path to face detector model directory")

def extract_face(filename, output_dir, net, size=SIZE, confidence_threshold=0.7):
    image = cv2.imread(filename)
    image_out = os.path.join(output_dir, filename.split('/')[-1])

    orig = image.copy()
    (h, w) = image.shape[:2]

    blob = cv2.dnn.blobFromImage(image, 1.0, (128, 128), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence < confidence_threshold:
            # Drop face detection has low confidence
            continue

        box = detections[0, 0, 0, 3:7] * np.array([w, h, w, h])
        (startX, startY, endX, endY) = box.astype("int")
        (startX, startY) = (max(0, startX), max(0, startY))
        (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

        frame = image[startY:endY, startX:endX]
        frame = cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)

        if i > 0:
            base_dir = os.path.dirname(image_out)
            base_file = '%s_%s.jpg' % (os.path.basename(image_out).split('.')[0], i)
            image_out = os.path.join(base_dir, base_file)

        status = cv2.imwrite(image_out, frame)

if __name__ == '__main__':
    args = parser.parse_args()

    assert os.path.isdir(args.data_dir), "Couldn't find the dataset at {}".format(args.data_dir)

    prototxtPath = os.path.join(args.face, "deploy.prototxt")
    weightsPath = os.path.join(args.face, "res10_300x300_ssd_iter_140000.caffemodel")
    net = cv2.dnn.readNet(prototxtPath, weightsPath)

    # Define the data directories
    train_mask_dir = os.path.join(args.data_dir, 'train/Mask')
    train_non_mask_dir = os.path.join(args.data_dir, 'train/Non Mask')

    test_mask_dir = os.path.join(args.data_dir, 'test/Mask')
    test_non_mask_dir = os.path.join(args.data_dir, 'test/Non Mask')

    # Get the filenames in each directory (train and test)
    filenames_mask = os.listdir(train_mask_dir)
    filenames_mask = [os.path.join(train_mask_dir, f) for f in filenames_mask if f.endswith('.jpg')]

    filenames_non_mask = os.listdir(train_non_mask_dir)
    filenames_non_mask = [os.path.join(train_non_mask_dir, f) for f in filenames_non_mask if f.endswith('.jpg')]

    test_filenames_mask = os.listdir(test_mask_dir)
    test_filenames_mask = [os.path.join(test_mask_dir, f) for f in test_filenames_mask if f.endswith('.jpg')]

    test_filenames_non_mask = os.listdir(test_non_mask_dir)
    test_filenames_non_mask = [os.path.join(test_non_mask_dir, f) for f in test_filenames_non_mask if f.endswith('.jpg')]

    # Split the images into 80% train and 20% dev
    # Make sure to always shuffle with a fixed seed so that the split is reproducible
    random.seed(161311)
    filenames_mask.sort()
    filenames_non_mask.sort()
    random.shuffle(filenames_mask)
    random.shuffle(filenames_non_mask)

    split_mask = int(0.8 * len(filenames_mask))
    train_filenames_mask = filenames_mask[:split_mask]
    dev_filenames_mask = filenames_mask[split_mask:]

    split_non_mask = int(0.8 * len(filenames_non_mask))
    train_filenames_non_mask = filenames_non_mask[:split_non_mask]
    dev_filenames_non_mask = filenames_non_mask[split_non_mask:]

    filenames = {'train/Mask': train_filenames_mask,
                 'train/Non Mask': train_filenames_non_mask,
                 'test/Mask': test_filenames_mask,
                 'test/Non Mask': test_filenames_non_mask,
                 'validation/Mask': dev_filenames_mask,
                 'validation/Non Mask': dev_filenames_non_mask}

    # Preprocess train, dev and test
    for split in filenames.keys():
        output_dir_split = os.path.join(args.output_dir, split)
        os.makedirs(output_dir_split, exist_ok=True)

        print("Processing {} data, saving preprocessed data to {}".format(split, output_dir_split))
        for filename in tqdm(filenames[split]):
            try:
                extract_face(filename, output_dir_split, net)
            except Exception as e:
                pass

    print("Done building dataset")