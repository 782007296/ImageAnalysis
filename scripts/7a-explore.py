#!/usr/bin/python

import argparse
import fnmatch
import os.path
from progress.bar import Bar
import sys
import time

import math
import numpy as np

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import LineSegs, NodePath, OrthographicLens, PNMImage, Texture

sys.path.append('../lib')
import ProjectMgr

parser = argparse.ArgumentParser(description='Set the initial camera poses.')
parser.add_argument('--project', required=True, help='project directory')
args = parser.parse_args()

proj = ProjectMgr.ProjectMgr(args.project)
proj.load_image_info()

ref = proj.ned_reference_lla

tcache = {}

class MyApp(ShowBase):
 
    def __init__(self):
        ShowBase.__init__(self)
 
        # Load the environment model.
        # self.scene1 = self.loader.loadModel("models/environment")
        self.models = []
        self.base_textures = []

        # we would like an orthographic lens
        self.lens = OrthographicLens()
        self.lens.setFilmSize(20, 15)
        base.camNode.setLens(self.lens)

        self.cam_pos = [ ref[1], ref[0], -ref[2] + 1000 ]
        self.camera.setPos(self.cam_pos[0], self.cam_pos[1], self.cam_pos[2])
        self.camera.setHpr(0, -89.9, 0)
        self.view_size = 100.0

        # test line drawing
        ls = LineSegs()
        ls.setThickness(1)
        ls.setColor(1.0, 0.0, 0.0, 1.0)
        ls.moveTo(-100, -100, 400)
        ls.drawTo(100, -100, 400)
        ls.drawTo(100, 100, 400)
        ls.drawTo(-100, 100, 400)
        ls.drawTo(-100, -100, 400)
        node = NodePath(ls.create())
        node.setBin("unsorted", 0)
        node.reparentTo(self.render)

        # setup keyboard handlers
        #self.messenger.toggleVerbose()
        self.accept('arrow_left', self.cam_move, [-1, 0, 0])
        self.accept('arrow_right', self.cam_move, [1, 0, 0])
        self.accept('arrow_down', self.cam_move, [0, -1, 0])
        self.accept('arrow_up', self.cam_move, [0, 1, 0])
        self.accept('=', self.cam_zoom, [1.1])
        self.accept('shift-=', self.cam_zoom, [1.1])
        self.accept('-', self.cam_zoom, [1.0 / 1.1])
        self.accept('escape', self.quit)
        
        # Add the tasks to the task manager.
        self.taskMgr.add(self.updateCameraTask, "updateCameraTask")

    def load(self, path):
        files = []
        for file in os.listdir(path):
            if fnmatch.fnmatch(file, '*.egg'):
                files.append(file)
        bar = Bar('Loading textures:', max=len(files))
	for file in files:
            # load and reparent each egg file
            model = self.loader.loadModel(os.path.join(path, file))
            model.reparentTo(self.render)
            self.models.append(model)
            tex = model.findTexture('*')
            tex.setWrapU(Texture.WM_clamp)
            tex.setWrapV(Texture.WM_clamp)
            self.base_textures.append(tex)
            bar.next()
        bar.finish()
        self.sortImages()

    def cam_move(self, x, y, z):
        self.cam_pos[0] += x * self.view_size / 10.0
        self.cam_pos[1] += y * self.view_size / 10.0
        self.sortImages()
        
    def cam_zoom(self, f):
        self.view_size /= f

    def quit(self):
        quit()
        
    # Define a procedure to move the camera.
    def updateCameraTask(self, task):
        self.camera.setPos(self.cam_pos[0], self.cam_pos[1], self.cam_pos[2])
        self.camera.setHpr(0, -90, 0)
        self.lens.setFilmSize(self.view_size*base.getAspectRatio(),
                              self.view_size)
        return Task.cont

    def sortImages(self):
        # sort images by depth
        result_list = []
        for m in self.models:
            b = m.getBounds()
            # print(b.getCenter(), b.getRadius())
            dx = b.getCenter()[0] - self.cam_pos[0]
            dy = b.getCenter()[1] - self.cam_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            result_list.append( [dist, m] )
        result_list = sorted(result_list, key=lambda fields: fields[0],
                             reverse=True)
        top = result_list[-1][1]
        top.setColor(1.0, 1.0, 1.0, 1.0)
        self.updateTexture(top)
        for i, line in enumerate(result_list):
            m = line[1]
            if m.getName() in tcache:
                # reward draw order for models with high res texture loaded
                m.setBin("fixed", i + len(self.models))
            else:
                m.setBin("fixed", i)
            m.setDepthTest(False)
            m.setDepthWrite(False)
            #if m != top:
            #    m.setColor(0.7, 0.7, 0.7, 1.0)

    def updateTexture(self, main):
        # reset base textures
        for i, m in enumerate(self.models):
            if m != main:
                if m.getName() in tcache:
                    fulltex = tcache[m.getName()][1]
                    self.models[i].setTexture(fulltex, 1)
                else:
                    self.models[i].setTexture(self.base_textures[i], 1)
            else:
                print(m.getName())
                base, ext = os.path.splitext(m.getName())
                fullpath = os.path.join(args.project, "Images", base + '.JPG')
                print(fullpath)
                fulltex = self.loader.loadTexture(fullpath)
                fulltex.setWrapU(Texture.WM_clamp)
                fulltex.setWrapV(Texture.WM_clamp)
                print('fulltex:', fulltex)
                m.setTexture(fulltex, 1)
                tcache[m.getName()] = [m, fulltex, time.time()]
        cachesize = 5
        while len(tcache) > cachesize:
            oldest_time = time.time()
            oldest_name = ""
            for name in tcache:
                if tcache[name][2] < oldest_time:
                    oldest_time = tcache[name][2]
                    oldest_name = name
            del tcache[oldest_name]
    
app = MyApp()
app.load( os.path.join(args.project, "Textures") )
app.run()
