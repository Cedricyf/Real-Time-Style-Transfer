import socket
import sys
import csv
import PIL.Image as Image
import io
from PIL import ImageFile
import os
import glob

ImageFile.LOAD_TRUNCATED_IMAGES=True

def sendCSVfile(file):
        out=[]
        for f in file:
            print ('reading file %s...' % f)
            csvfile = open(f, 'rb')
            reader = csvfile.read()
            for row in reader:
                out+=[row]
        return out

HOST, PORT = '127.0.0.1', 9999

# List of images need to be sent to the server
list1=[['tqs.jpg' , 'classproject2server/Lacafetiere.jpg']]

# Create a socket (SOCK_STREAM means a TCP socket)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    sent = 0
    num=1
    for l in list1:
        for im in l:
            f = open(im, 'rb')
            image_bytes = f.read()
            length = len(image_bytes)
            if not image_bytes:
                break
            size_info=bytes(str(length),'utf-8')
            if sent == 0:
                sock.sendall(size_info)
                sent = 1
            sock.sendall(image_bytes)
            f.close()
        image=b''
        sent=0
        # Receive data from the server and shut down
        while True:
            received = sock.recv(4096)
            image+=received
            if len(received)!=4096:
                break
        image = Image.open(io.BytesIO(image))
        # Save transferred image
        image_name='client1_'+str(num)+'.jpg'
        image.save(image_name)
        num+=1
        print('Image Received!')


