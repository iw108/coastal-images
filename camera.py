# -*- coding: utf-8 -*-
"""
Created on Sat Apr 28 09:12:15 2018

@author: isaacwilliams
"""

# Drad, Dtan, K, shape

import cv2
import numpy as np
import urllib
from fourier import Fourier, get_taper


_COLORSPACES = ['RGB', 'LAB', 'GRAY', 'UNDEFINED']


class Camera:

    R, t, proj_error = None, None, None


    def __init__(self, K, Drad, Dtan, Nu, Nv):
        self.K = K
        self.Drad = Drad
        self.Dtan = Dtan
        self.Nu = Nu
        self.Nv = Nv


    @property
    def frame_size(self):
        return (self.Nu, self.Nv)


    @property
    def distcoefs(self):

        Dtan = self.Dtan
        Drad1, Drad2 = self.Drad[0:2], self.Drad[2:]
        coefs = np.concatenate([Drad1, Dtan, Drad2])

        pad = [0] * (8 - coefs.shape[0])
        coefs = np.concatenate((coefs, pad))

        return coefs[0:8]


    @property
    def Kopt(self):
        return cv2.getOptimalNewCameraMatrix(self.K, self.distcoefs, self.frame_size, 0, self.frame_size)[0]


    @property
    def fov(self):
        return 2*np.arctan(self.Nu/(2 * self.Kopt[0, 0]))


    # Undistort image coordinates
    def undistort(self, uv):
        uvprime = cv2.undistortPoints(uv.reshape(-1, 1, 2),
                                         self.K, self.distcoefs, P = self.Kopt)
        return uvprime.reshape(uv.shape)


    # Undistort image
    def undistortimg(self, img):
        return cv2.undistort(img, self.K, self.distcoefs, self.Kopt)


    # Image coordinates to cylindrical
    def uv2cyl(self, u, v):

        Kopt = self.Kopt
        f, u0, v0 = Kopt[0, -1], Kopt[1, -1],  Kopt[0, 0]

        ucyl = f * (np.arctan((u - u0)/ f)) + u0
        vcyl = f * ((v - v0)/ np.sqrt((u - u0)**2+ f**2)) + v0
        return ucyl, vcyl


    # Rectify
    def rectify(self, xyz, uv, distort = False):
        if distort:
            uv = self.undistort(uv)

        rvec, self.t = cv2.solvePnP(xyz, uv, self.Kopt, np.array([0, 0, 0, 0]))[-2:]
        self.R = cv2.Rodrigues(rvec)[0]
        self.proj_error = np.mean(np.sqrt(np.sum((self.xyz2uv(xyz).data - uv)**2, axis = 1)))


    # xyz to image coordinates
    def xyz2uv(self, xyz):

        if not isinstance(self.R, np.ndarray) or not isinstance(self.t, np.ndarray):
            raise ValueError('Camera has to be rectified')

        Kopt = self.Kopt

        xyzprime = np.sum(self.R * xyz.reshape(-1, 1, 3), axis = 2) + self.t.reshape(1, -1)
        xyzprime /= np.tile(xyzprime[:, -1], (3, 1)).T

        u = Kopt[0, 0] * xyzprime[:, 0]/xyzprime[:, -1] + Kopt[0, 2]
        v = Kopt[1, 1] * xyzprime[:, 1]/xyzprime[:, -1] + Kopt[1, 2]

        mask =  np.isnan(u) | np.isnan(v)

        mask[~mask] = ((u[~mask] < 0) | (u[~mask] >= self.Nu) |
                            (v[~mask] < 0) | (v[~mask] >= self.Nv))

        return np.ma.masked_array(np.column_stack((u, v)), mask = np.column_stack((mask, mask)))


    # see if xy coordinates in fov
    def xyinfov(self, x, y):

        if not isinstance(self.R, np.ndarray) or not isinstance(self.t, np.ndarray):
            raise ValueError('Camera has to be rectified')

        shape = x.shape
        xyz = np.column_stack((x.ravel(), y.ravel(), np.zeros((x.size, ))))
        xzy = np.dot(self.R, xyz.T).T + self.t.flatten()
        theta = np.abs(np.arctan2(xzy[:, 0], xzy[:, -1]))
        mask = (xzy[:, -1] < 0) | (theta > self.fov/2)

        return ~mask.reshape(shape)



    def makegrid(self, ds, radial):

        if not isinstance(self.R, np.ndarray) or not isinstance(self.t, np.ndarray):
            raise ValueError('Camera has to be rectified')


        xn, yn  = np.array([]), np.array([])
        for r in radial:
            dtheta = ds/r
            N = 2*int(self.fov/dtheta/2)
            n = np.arange(1, N)
            theta = (n - N/2) * dtheta
            xn, yn  = np.concatenate((xn, r * np.cos(theta))), np.concatenate((yn, r * np.sin(theta)))

        mat = np.column_stack((yn, np.zeros(xn.shape), xn)) - self.t.flatten()
        Rinv = np.linalg.inv(self.R)
        xy = np.dot(Rinv, mat.T).T[:, 0: 2]
        return xy




class Regionofinterest:

    def __init__(self, corners):
        self.corners = corners


    @property
    def widths(self):
        return np.max(self.corners, axis = 0) - np.min(self.corners, axis = 0)


    @property
    def minwidth(self):
        return min(self.widths)


    @property
    def lengths(self):
        lengths = np.array([np.sqrt(np.sum((self.corners[0] - self.corners[2])**2)),
                               np.sqrt(np.sum((self.corners[1] - self.corners[3])**2))])
        return lengths


    def warpPerspective(self, img, shape = None):

        if not shape:
            shape = (int(self.minwidth), int(self.minwidth))


        dst = np.array([[0, 0], [shape[0], 0], [shape[0], shape[1]], [0, shape[1]]], dtype = "float32")
        M = cv2.getPerspectiveTransform(self.corners.astype('float32'), dst)
        warped = cv2.warpPerspective(img, M, shape)

        return warped, M


    def extractroi(self, img):

        corners_int = self.corners.astype(int)
        frame_size = np.asarray((img.shape[0: 2]))

        col_min, row_min = np.min(corners_int, axis = 0)
        col_max, row_max = np.max(corners_int, axis = 0)

        col_limits = [max(col_min, 0), min(col_max, frame_size[1])]
        row_limits = [max(row_min, 0), min(row_max, frame_size[0])]

        image_mask = np.zeros(frame_size).astype(bool)
        image_mask[row_limits[0]:row_limits[1], col_limits[0]: col_limits[1]] = 1

        roi_size = (row_max - row_min, col_max - col_min)
        roi_mask = np.zeros(roi_size).astype(bool)
        roi_mask[row_limits[0] - row_min: row_limits[1] - row_min,
                          col_limits[0] - col_min: col_limits[1] - col_min] = 1
        roi_corners = corners_int - [col_min, row_min]

        if len(img.shape) == 3:
            roi = np.zeros((*roi_size, 3))
        else:
            roi = np.zeros(roi_size)
        roi[roi_mask] = img[image_mask]
        roi = roi.astype(img.dtype)

        mask = cv2.fillConvexPoly(np.zeros((roi_size)), roi_corners, 4, 1) == 0
        return roi, mask, roi_corners


class Image(object):


    def __init__(self, image, colorspace = 'UNDEFINED'):

       self._image = self._parse_image(image)
       self.colorspace = self._parse_colorspace(colorspace)


    @property
    def mean(self):
        return np.mean(self._image, axis = (0, 1))


    @property
    def shape(self):
        return self._image.shape


    @property
    def framesize(self):
        return self._image.shape[0:2]


    @property
    def nchannels(self):
        if np.ndim(self._image) == 2:
            return 1
        elif np.ndim(self._image) == 3:
            return 3


    @property
    def channels(self):
        if self.nchannels == 1:
            return [self.image]
        else:
            return [channel.reshape(self.framesize) for channel in np.dsplit(self._image, 3)]


    @property
    def image(self):
        return self._image.copy()



    def blur(self,  kernal = (3, 3), weight = 0, inplace = False):
        if inplace:
            self._image = cv2.GaussianBlur(self._image, kernal, weight)
            return self
        else:
            return cv2.GaussianBlur(self._image, kernal, weight)



    def resize(self, shape, inplace = False):
        if inplace:
            self._image = cv2.resize(self._image, shape)
            return self
        else:
           return cv2.resize(self._image, shape)



    def rotate(self, ang, mode = 'deg', inplace = False):
        if mode == 'rad':
            ang *=  np.pi/180

        image = self.image
        if ang != 0 or ang != 360:
            M = cv2.getRotationMatrix2D(tuple([dim/ 2 for dim in self.framesize]), ang, 1)
            image = cv2.warpAffine(image, M, self.framesize)

        if inplace:
            self._image = image
            return self
        else:
            return image


    def color_transfer(self, reference, inplace = False):

        if reference.size != self.nchannels:
            raise ValueError('Reference array doesnt equal image dimensions')

        channels = []
        for ref, channel in zip(reference, self.channels):
            channel += (ref - np.mean(channel))
            channels.append(channel)

        image = np.dstack(channels).reshape(self.shape)
        image = self.scale_colors(image, self.colorspace)

        if inplace:
            self._image = image
            return self
        else:
            return image


    def taper(self, method, alpha = 0.2, beta = 0.1, inplace = True):
        weights = get_taper(method, self.framesize, alpha = alpha, beta = beta)
        weights = weights.astype(np.float32)

        channels = []
        for idx, channel in enumerate(self.channels):
             wm = np.nansum(channel*weights)/np.sum(weights)
             channels.append(channel * weights + (1 - weights) * wm)

        if idx == 0:
            channels = channels[0]
        else:
            channels = np.dstack(channels)

        image = self.scale_colors(channels, self.colorspace)
        if inplace:
            self._image = image
            return self
        else:
            return image


    def togray(self, inplace = False):

       if self.colorspace == 'LAB':
           image = cv2.cvtColor(self._image, cv2.COLOR_LAB2RGB)
           image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

       elif self.colorspace == 'RGB':
           image = cv2.cvtColor(self._image, cv2.COLOR_RGB2GRAY)

       elif self.colorspace == 'GRAY':
           image = self.image

       elif self.colorspace == 'UNDEFINED':
           raise TypeError("Can't convert colorspace to LAB")


       if inplace:
           self._image = image
           self.colorspace = 'GRAY'
           return self
       else:
           return image



    def tolab(self, inplace = False):

        if self.colorspace == 'RGB':
            image = cv2.cvtColor(self._image, cv2.COLOR_RGB2LAB)

        elif self.colorspace == 'LAB':
            image = self.image

        elif self.colorspace == 'GRAY' or self.colorspace == 'UNDEFINED':
            raise TypeError("Can't convert colorspace to LAB")


        if inplace:
            self._image = image
            self.colorspace = 'LAB'
            return self
        else:
            return image



    def torgb(self, inplace = False):

        if self.colorspace == 'LAB':
            image = cv2.cvtColor(self._image, cv2.COLOR_LAB2RGB)
        elif self.colorspace == 'RGB':
            image = self.image
        elif self.colorspace == 'GRAY' or self.colorspace == 'UNDEFINED':
            raise TypeError("Can't convert colorspace to RGB")

        if inplace:
            self._image = image
            self.colorspace = 'RGB'
            return self
        else:
            return image



    def band_pass(self, u = None, v = None, kmin = 0, kmax = np.inf, inplace = False, **kwargs):

        if isinstance(u, np.ndarray):
            if u.size != self.framesize[1]:
                raise ValueError('u incorrect shape')
        else:
            u = np.arange(self.framesize[1])


        if isinstance(v, np.ndarray):
            if v.size != self.framesize[0]:
                raise ValueError('v incorrect shape')
        else:
            v = np.arange(self.framesize[0])


        image = []
        channels = self.channels
        for channel in channels:
            transform = Fourier.transform(u, v, channel, remove_avg = True)
            if 'Lmin' in kwargs.keys():
                try:
                    kmax = 2*np.pi/kwargs['Lmin']
                except ZeroDivisionError:
                    kmax = np.inf
            if 'Lmax' in kwargs.keys():
                kmin = 2*np.pi/kwargs['Lmax']

            filtered = transform.band_pass(kmax = kmax, kmin = kmin).reverse()
            image.append(filtered.astype(np.float32))


        if len(image) == 1:
            image = image[0]
        else:
            image = np.dstack(image)

        image = self.scale_colors(image, self.colorspace)

        if inplace:
            self._image = image
            return self
        else:
            return image



    @staticmethod
    def _parse_image(image):

        if not image.dtype == np.dtype(np.float32):
            raise TypeError('Input image should be of type numpy.float32')

        return image


    @staticmethod
    def _parse_colorspace(colorspace):

        if not isinstance(colorspace, str) or not colorspace in _COLORSPACES:
            raise TypeError("Colorspace must be string from: {}".format(_COLORSPACES))

        return colorspace


    @staticmethod
    def scale_colors(image, colorspace):
        if colorspace == 'RGB' or colorspace == 'GRAY':
             image[image < 0] = 0
             image[image > 1] = 1
        elif colorspace == 'LAB':
           channels = [channel.reshape(image.shape[0:2]) for channel in np.dsplit(image, 3)]
           limits = [(0, 100), (-128, 128), (-128, 128)]
           for idx, (limit, channel) in enumerate(zip(limits, channels)):
               channels[idx] = np.clip(channel, *limit)
           image = np.dstack(channels)

        return image
