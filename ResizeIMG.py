import cv2
import os

filenames = os.listdir("/Users/pengkun/Desktop/dada")
filenames.sort(key=lambda x: int(x[-8:-4]))
for i, path in enumerate(filenames):
    if path[-3:] == 'jpg':
        print(path)
        img = cv2.imread("/Users/pengkun/Desktop/dada/" + path)
        resized = cv2.resize(img, (int(img.shape[1]/5), int(img.shape[0]/5)), interpolation=cv2.INTER_AREA)
        name = "/Users/pengkun/Desktop/dada/" + str(i) + '.jpg'
        cv2.imwrite(name, resized)
