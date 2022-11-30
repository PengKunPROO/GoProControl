import cv2
import os

video_path = ''
output_img_path = ''

camera = cv2.VideoCapture(video_path)
frames = camera.get(cv2.CAP_PROP_FRAME_COUNT)

times = 0
while True:
    times += 1
    if times == int(frames/2):
        res, image = camera.read()
        cv2.imwrite(output_img_path, image)
        break

camera.release()