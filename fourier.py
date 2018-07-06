#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  2 16:53:39 2018

@author: williamsia
"""


import numpy as np


def _prepare_dataset(data, taper = False, alpha = 0.2, beta = 0.1, avg=False):


    if taper:
        weights = get_taper(taper, data.shape, alpha = alpha, beta = beta)
        wm = np.nansum(data*weights)/np.sum(weights)
        data = data * weights + (1 - weights) * wm

    if avg:
        offset = np.nanmean(data)
        data -= offset   
    else:
        offset = 0

    return data, offset



class Fourier:
    
    def __init__(self, kx, ky, S, cellsize=25, area=None, offset = 0):
        
        self.kx = kx
        self.ky = ky
        self.S = S
 
       
        self.offset = offset

        if isinstance(cellsize, int):
            cellsize = (cellsize, cellsize)
        self.cellsize = cellsize

        if area is None:
            # area = cellsize[0] * S.shape[0] * cellsize[1] * S.shape[1]
            area = S.shape[0] * S.shape[1]
        self.area = area



    @property
    def shape(self):
        """return the shape of the fourier transform spectrum"""
        return self.S.shape


    @property
    def amplitude(self):
        """return the amplitude as 2*abs(S/datasize)"""
        return 2*np.absolute(self.S/self.area)


    @property
    def steepness(self):
        """return the steepness as H*K or H/L with H = 2*amplitude"""
        return 2* self.amplitude * self.K


    @property
    def K(self):
        """return a matrix with the wave numbers"""
        Kx, Ky = np.meshgrid(self.kx, self.ky)
        return (Kx**2+Ky**2)**.5


    @classmethod
    def transform(cls, x, y, Z, taper=False, alpha = 0.2, beta = 0.2, remove_avg=False):
        """
        returns a shifted fourier transform (fft2) of the data

        :param x: numpy array (1D) with x coordinates
        :param y: numpy array (1D) with y coordinates
        :param Z: numpy array (2D) with data values (no numpy MaskedArray)
        :return: Fourier object

        the returned value is is Fourier object with the following important attributes:
        .kx         wave number in horizontal direction
        .ky         wave number in vertical direction
        .S          spectrum
        .K          absolute wave number (kx**2+ky**2)**.5
        .amplitude  amplitude representation
        .steepness  amplitude*absolute wave number
        .shape      shape of the spectrum

        and the following methods:
        .reverse()        reverse the fourier to retrieve the data
        .plot(axes)       plot the fourier transform on the supplied axis
        .apply_mask(mask) multiplies the spectrum by the supplied mask to modify the spectrum (eg. filtering)
        """
        
        # difference first 2 values along x and y
        cellsize = (np.abs(x[1] - x[0]), np.abs(y[1] - y[0]))
                
        if (np.absolute(np.diff(x) - cellsize[0]) > cellsize[0]*.001).any():
            raise ValueError('x not equally spaced')
        if (np.absolute(np.diff(y) - cellsize[1]) > cellsize[1]*.001).any():
            raise ValueError('y not equally spaced')


        Z, offset = _prepare_dataset(Z, taper=taper, alpha = alpha, beta = beta, avg =remove_avg)

        # create wave number vectors
        kx = np.linspace(-.5, .5, Z.shape[1])/cellsize[1]
        ky = np.linspace(-.5, .5, Z.shape[0])/cellsize[0]

        # spectrum
        S = np.fft.fftshift(np.fft.fft2(Z))

        # return a fourier object
        return cls(kx, ky, S, cellsize = cellsize, offset = offset)


    def reverse(self, shape = None):
        """
        return a dataset from the fourier spectrum

        :param shape: shape of the output (should be equal to the original dataset)
        :param nanmask: numpy bool array of nan values where true means to mask
        :return: new dataset
        """

        # determine shape
        if shape is None:
            shape = self.kx.shape[0], self.ky.shape[0]

        # shift spectrum
        S = np.fft.ifftshift(self.S)

        # reverse fourier of spectrum
        data = np.real(np.fft.ifft2(S, shape)) + self.offset

        return data



    def apply_mask(self, m, shift=False):
        """

        :param m:
        :param shift:
        :return:
        """
        if shift:
            m = np.fft.fftshift(m)

        S = self.S*m

        return type(self)(self.kx, self.ky, S, cellsize=self.cellsize,
                                          area=self.area, offset = self.offset)
        


    def band_pass(self, kmin=0, kmax=np.inf, **kwargs):
    
        if 'Lmin' in kwargs.keys():
            try:
                kmax = 2*np.pi/kwargs['Lmin']
            except ZeroDivisionError:
                kmax = np.inf
        
        if 'Lmax' in kwargs.keys():
            kmin = 2*np.pi/kwargs['Lmax'] 
    
        mask = (self.K > kmin) & (self.K < kmax)
        
        return self.apply_mask(mask)
    
    
    
    def get_dir(self, angularbin = 30, threshold = 0.5):
  
        kx, ky = np.meshgrid(self.kx, self.ky)
        
        
        mask = (self.amplitude/self.amplitude.max()) > threshold

        # regression through points 
        m = np.linalg.lstsq(kx[mask][:, np.newaxis], ky[mask], rcond = None)[0][0]    
        rsq = 1 - np.sum((ky[mask] - m*kx[mask])**2)/ np.sum((ky[mask] - np.mean(ky[mask]))**2)        

        
        # Find orientation of image features about y axis
        gradient = -1/m  
        if gradient > 0:
            theta = np.pi/2 - np.arctan(gradient)
        elif gradient < 0:
            theta = np.pi/2 + np.abs(np.arctan(gradient))
        theta *= 180/np.pi
       
        # Energy check - find angle between wave number pairs and line (dot product) 
        kx1, ky1 =  kx.min(), m*kx.min()
        with np.errstate(divide = 'ignore', invalid = 'ignore'):
            dtheta = ((kx * kx1 + ky * ky1)/ 
                          (np.sqrt(kx1**2 + ky1**2)*np.sqrt(kx**2 + ky**2)))
        dtheta[np.isnan(dtheta)] = np.inf
        
        
        mask = np.abs(dtheta) >=  np.cos(angularbin/2 * np.pi/180)
        energy = np.sum(self.amplitude[mask]**2)/ np.sum(self.amplitude**2)
        
        return rsq, energy, gradient, theta    



    def filter2(self, kmin=0, kmax=np.inf, theta=None, theta_offset=180, dirmode='deg', spatial_frequencies=True):
        """
        Filter the spectrum based on wave number or angle
        :param kmin: mimumum wave number as spatial or angular (see spatial_frequencies) with default 0
        :param kmax: maximum wave number as spatial or angular (see spatial_frequencies) with default np.inf
        :param theta: mean angle of features to keep
        :param theta_offset: offset from theta to either side
        :param dirmode: specifies angle definition (deg|rad)
        :param spatial_frequencies: specifies if wave numbers are spatial (1/L) or angular (2pi/L)
        :return: new Fourier object with masked frequencies
        """
        if spatial_frequencies:
            kmin = 2 * np.pi * kmin
            kmax = 2 * np.pi * kmax

        mask = (self.K > kmin) & (self.K < kmax)

        if theta is not None:
            if dirmode == 'deg':
                theta = theta * np.pi / 180
                theta_offset = theta_offset * np.pi / 180
            elif dirmode == 'rad':
                pass
            else:
                raise ValueError('invalid direction mode')

            x = np.linspace(-1, 1, self.kx.size)
            y = np.linspace(-1, 1, self.ky.size)
            X, Y = np.meshgrid(x, y)
            angle_diff = np.absolute((theta - np.arctan2(Y, X) + .5 * np.pi) % np.pi - .5 * np.pi)

            mask = np.logical_and(mask, angle_diff <= theta_offset)

        return self.apply_mask(mask)


_TAPERS = ['Tophat', 'Cosinebell', 'Tukey', 'Hanning', 'Splitcosinebell']


def get_taper(mode, shape, alpha = 0.2, beta = 0):

    if mode not in _TAPERS:
        raise ValueError("input taper doesn't exist")
    
    elif mode == 'Tophat':
        taper = TopHatWindow(beta)
    
    elif mode == 'Cosinebell':
        taper = CosineBellWindow(alpha)
    
    elif mode == 'Tukey':
        taper = TukeyWindow(alpha)
    
    elif mode == 'Hanning':
        taper = HanningWindow()
    
    elif mode == 'Splitcosinebell':
        taper = SplitCosineBellWindow(alpha, beta)

    return taper(shape[0:2])



def _radial_distance(shape):
    """
    Return an array where each value is the Euclidean distance from the
    array center.
    Parameters
    ----------
    shape : tuple of int
        The size of the output array along each axis.
    Returns
    -------
    result : `~numpy.ndarray`
        An array containing the Euclidian radial distances from the
        array center.
    """

    if len(shape) != 2:
        raise ValueError('shape must have only 2 elements')
    position = (np.asarray(shape) - 1) / 2.
    x = np.arange(shape[1]) - position[1]
    y = np.arange(shape[0]) - position[0]
    xx, yy = np.meshgrid(x, y)
    return np.sqrt(xx**2 + yy**2)


class SplitCosineBellWindow(object):
    """
    Class to define a 2D split cosine bell taper function.
    Parameters
    ----------
    alpha : float, optional
        The percentage of array values that are tapered.
    beta : float, optional
        The inner diameter as a fraction of the array size beyond which
        the taper begins. ``beta`` must be less or equal to 1.0.
    Examples
    --------
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import SplitCosineBellWindow
        taper = SplitCosineBellWindow(alpha=0.4, beta=0.3)
        data = taper((101, 101))
        plt.imshow(data, cmap='viridis', origin='lower')
        plt.colorbar()
    A 1D cut across the image center:
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import SplitCosineBellWindow
        taper = SplitCosineBellWindow(alpha=0.4, beta=0.3)
        data = taper((101, 101))
        plt.plot(data[50, :])
    """

    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta

    def __call__(self, shape):
        """
        Return a 2D split cosine bell.
        Parameters
        ----------
        shape : tuple of int
            The size of the output array along each axis.
        Returns
        -------
        result : `~numpy.ndarray`
            A 2D array containing the cosine bell values.
        """

        radial_dist = _radial_distance(shape)
        npts = (np.array(shape).min() - 1.) / 2.
        r_inner = self.beta * npts
        r = radial_dist - r_inner
        r_taper = int(np.floor(self.alpha * npts))

        if r_taper != 0:
            f = 0.5 * (1.0 + np.cos(np.pi * r / r_taper))
        else:
            f = np.ones(shape)

        f[radial_dist < r_inner] = 1.
        r_cut = r_inner + r_taper
        f[radial_dist > r_cut] = 0.

        return f


class HanningWindow(SplitCosineBellWindow):
    """
    Class to define a 2D `Hanning (or Hann) window
    <https://en.wikipedia.org/wiki/Hann_function>`_ function.
    The Hann window is a taper formed by using a raised cosine with ends
    that touch zero.
    Examples
    --------
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import HanningWindow
        taper = HanningWindow()
        data = taper((101, 101))
        plt.imshow(data, cmap='viridis', origin='lower')
        plt.colorbar()
    A 1D cut across the image center:
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import HanningWindow
        taper = HanningWindow()
        data = taper((101, 101))
        plt.plot(data[50, :])
    """

    def __init__(self):
        self.alpha = 1.0
        self.beta = 0.0


class TukeyWindow(SplitCosineBellWindow):
    """
    Class to define a 2D `Tukey window
    <https://en.wikipedia.org/wiki/Window_function#Tukey_window>`_
    function.
    The Tukey window is a taper formed by using a split cosine bell
    function with ends that touch zero.
    Parameters
    ----------
    alpha : float, optional
        The percentage of array values that are tapered.
    Examples
    --------
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import TukeyWindow
        taper = TukeyWindow(alpha=0.4)
        data = taper((101, 101))
        plt.imshow(data, cmap='viridis', origin='lower')
        plt.colorbar()
    A 1D cut across the image center:
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import TukeyWindow
        taper = TukeyWindow(alpha=0.4)
        data = taper((101, 101))
        plt.plot(data[50, :])
    """

    def __init__(self, alpha):
        self.alpha = alpha
        self.beta = 1. - self.alpha


class CosineBellWindow(SplitCosineBellWindow):
    """
    Class to define a 2D cosine bell window function.
    Parameters
    ----------
    alpha : float, optional
        The percentage of array values that are tapered.
    Examples
    --------
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import CosineBellWindow
        taper = CosineBellWindow(alpha=0.3)
        data = taper((101, 101))
        plt.imshow(data, cmap='viridis', origin='lower')
        plt.colorbar()
    A 1D cut across the image center:
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import CosineBellWindow
        taper = CosineBellWindow(alpha=0.3)
        data = taper((101, 101))
        plt.plot(data[50, :])
    """

    def __init__(self, alpha):
        self.alpha = alpha
        self.beta = 0.0


class TopHatWindow(SplitCosineBellWindow):
    """
    Class to define a 2D top hat window function.
    Parameters
    ----------
    beta : float, optional
        The inner diameter as a fraction of the array size beyond which
        the taper begins. ``beta`` must be less or equal to 1.0.
    Examples
    --------
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import TopHatWindow
        taper = TopHatWindow(beta=0.4)
        data = taper((101, 101))
        plt.imshow(data, cmap='viridis', origin='lower',
                   interpolation='nearest')
        plt.colorbar()
    A 1D cut across the image center:
    .. plot::
        :include-source:
        import matplotlib.pyplot as plt
        from photutils import TopHatWindow
        taper = TopHatWindow(beta=0.4)
        data = taper((101, 101))
        plt.plot(data[50, :])
    """

    def __init__(self, beta):
        self.alpha = 0.0
        self.beta = beta



