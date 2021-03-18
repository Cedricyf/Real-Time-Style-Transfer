#!/usr/bin/env python3
import socket
import threading
import csv
import json
import argparse
import sys
import time
import datetime
import PIL.Image as Image
import io
from trans_model import run_style_transfer, get_style_model_and_losses, image_loader
import torchvision.models as models
import torch
import torchvision.transforms as transforms
from multiprocessing import Process


class Server(object):
    def __init__(self, host, opt):
        self.environment = {}
        self.environment['NoMode'] = {'points': 0}
        self.environment['Occupancy'] = {'occupancy': 0, 'points': 0}
        self.host = host
        self.port = opt.port
        self.opt = opt
        self.state = self.environment[opt.mode if opt.mode else 'NoMode']
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        #self.lock = threading.Lock()
        self.content_img = None
        self.style_img = None
        self.image_out = None

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(30)
            p = Process(target=self.listenToClient, args=(client, address))
            #p.daemon = True
            p.start()
            #hreads=threading.Thread(target=self.listenToClient, args=(client, address))
            #threads.setDaemon(True)
            #threads.start()
            #threads.join()

    def handle_client_answer(self, obj):
        if self.opt.mode is not None and self.opt.mode == 'Occupancy':
            if 'Occupancy' not in obj:
                return
            self.lock.acquire()
            if self.state['occupancy'] == int(obj['Occupancy']):
                self.state['points'] += 1
            self.lock.release()
        return

    def listenToClient(self, client, address):
        size = 4096
        combined = b''
        length = 0
        len_idx=6
        while True:
            data = client.recv(size)
            try:
                if length == 0:
                    print(data)
                    # Get image size info
                    length = int(data[:len_idx].decode())
                    print(length)
                    combined += data[len_idx:]
                else:
                    if len(data)==size:
                        combined += data
                    else:
                        combined += data
                        combined1 = combined[0:length]
                        combined2 = combined[length:]
                        # Get content and style image
                        self.content_img = Image.open(io.BytesIO(combined1))
                        self.style_img = Image.open(io.BytesIO(combined2))
                        #self.content_img.save('reconstruct1.jpg')
                        #self.style_img.save('reconstruct2.jpg')
                        self.style_transfer(client)
                        combined = b''
                        length = 0
                        print('Picture Received')
            except:
                print('Client closed the connection')
                #print("Unexpected error:", sys.exc_info()[0])
                client.close()
                break

    def handleCustomData(self, buffer):
        if self.opt.mode is not None and self.opt.mode == 'Occupancy':
            self.lock.acquire()
            buffer['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.state['occupancy'] = int(buffer['Occupancy'])
            buffer['Occupancy'] = -1
            self.lock.release()

    def sendStreamToClient(self, client, buffer):
        for i in buffer:
            self.handleCustomData(i)
            try:
                while True:
                    chunk=i.read(4096)
                    if len(chunk)==0:
                        break
                    client.send(chunk)
                    time.sleep(self.opt.interval)
            except:
                print('End of stream')
                return False
        return False

    def style_transfer(self,client):
        print('Transfering...')
        #self.lock.acquire()
        imsize=512
        loader = transforms.Compose([
            transforms.Resize(imsize),  # scale imported image
            transforms.ToTensor()])
        # Make size for content and style image equal
        if self.style_img.size != self.content_img.size:
            new_size = self.content_img.size
            self.style_img = self.style_img.resize(new_size)
        self.style_img = image_loader(self.style_img,loader)
        self.content_img = image_loader(self.content_img,loader)
        assert self.style_img.size() == self.content_img.size()
        device = torch.device("cpu")
        cnn = models.vgg19(pretrained=True).features.to(device).eval()
        #self.lock.release()
        self.output_img = run_style_transfer(cnn, self.content_img, self.style_img,self.content_img,style_weight=100000)
        self.image_out = self.output_img.squeeze(0)  # remove the fake batch dimension
        unloader = transforms.ToPILImage()
        self.image_out = unloader(self.image_out)
        self.image_out.save('classproject2server/output_img.jpg')
        self.sendStreamToClient(client, self.sendImage())

    def sendImage(self):
        print('Sending...')
        out=[]
        imgfile = open('classproject2server/output_img.jpg', 'rb')
        out+=[imgfile]
        return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage='usage: tcp_server -p port [-f -m]')
    parser.add_argument('-f', '--files', nargs='+')
    parser.add_argument("-m", "--mode", action="store", dest="mode")
    parser.add_argument("-p", "--port", action="store", dest="port", type=int)
    parser.add_argument("-t", "--time-interval", action="store",
                        dest="interval", type=int, default=1)

    opt = parser.parse_args()
    if not opt.port:
        parser.error('Port not given')
    ThreadedServer = Server('127.0.0.1', opt).listen()

