import numpy as np 
import scipy.linalg

class metrics:
	def __init__(self, **kwargs):
		"""
		Utility function module
		"""
		self.__dict__.update(kwargs)

	def rms(self,x1,x2):
		"""
		Calculates root mean square error

		Input params:
		--------------
		x1 : numpy.ndarray
		x2 : numpy.ndarray
		
		returns:
		--------------
		rms : float
		"""
		return np.nanmean(np.sqrt(np.square(x2 - x1)))

	def R2(self,data,op,poly,k,adj=False):
		"""
		R-square value between the predicted and expected values

		Input params:
		--------------
		data : numpy.ndarray
			depended variable data of expected values
		op : numpy.ndarray
			independent variable values
		poly : numpy.poly1d
			the fit polynomial
		k : int
			degree of polynomial fit
		adj : bool
			if True, use R2-adjusted method instead of R2

		returns:
		--------------
		R2 : float
			R2 or R2-adjusted depending upon 'adj' value
		"""
		if adj: return self.R2_adj(data, op, poly, k)
		return 1 - (np.nanmean(np.square(data - poly(op)))/np.nanmean(np.square(data - np.nanmean(data))))

	def R2_adj(self, data, op, poly, k):
		"""
		R-squared adjusted method
		"""
		r2 = 1 - (np.nanmean(np.square(data - poly(op)))/np.nanmean(np.square(data - np.nanmean(data))))
		n = len(op)
		return 1-(((1-r2)*(n-1))/(n-k-1))

	def fit_poly(self,x,y,deg):
		"""
		Fits polynomial f(x) = y

		Input params:
		--------------
		x  : numpy.ndarray
			independent variable
		y : numpy.ndarray
			depended variable
		deg : int
			degree of the polynomial

		returns:
		-------------
		poly : np.poly1d
			polynomial object
		x : numpy.ndarray
			values of x for where y in defined
		"""
		nan_idx = np.argwhere(np.isnan(y))
		x_ = np.delete(x,nan_idx)
		y_ = np.delete(y,nan_idx)
		z = np.polyfit(x_,y_,deg)
		return np.poly1d(z), x_

	def nan_helper(self, x):
		"""
		Helper function used to handle missing data

		Input params:
		-------------
		x : numpy.ndarray
			data

		returns:
		-------------
		np.isnan(x) : numpy.array
			array of bools, true if x is numpy.nan else false
		z : callable function

		"""
		return np.isnan(x), lambda z: z.nonzero()[0]

	def interpolate_missing(self, y):
		"""
		Interpolate missing data

		Input params:
		-------------
		y : numpy.array
			array with missing (nan) values

		returns:
		-------------
		y : numpy.array
			missing values are interpolated
		"""
		nans, x = self.nan_helper(y)
		y[nans] = np.interp(x(nans), x(~nans), y[~nans])
		return y

	def kl_divergence(self, p, q):
		"""
		Calculates KL divergence between two probablity distrubitions

		Input params:
		-------------
		p : np.array
			distrubution p
		q : np.array
			distrubution q

		returns:
		-------------
		kl_divergence : float
			kl divergence between p and q

		"""
		k = p*np.log(np.abs(((p+1e-100)/(q+1e-100))))
		#k[np.where(np.isnan(k))] = 0
		return np.sum(k)

	def fit_plane(self, x,y,z, order=2, inc_x=0.1, inc_y=0.1, range_x=(-1,1), range_y=(-1,1)):
		"""
		Fits first order or second order plane to the surface data points

		Input params:
		-------------
		x : numpy.ndarray
			x values of meshgrid
		y : numpy.ndarray
			y values of meshgrid
		z : numpy.ndarray
			data points, function of x and y [z = f(x,y)]
		order = 2 : int
			1 or 2, order of the plane to fit
		inc_x = 0.1 : float
			increment in x
		inc_y = 0.1 : float
			increment in y
		range_x = (-1,1) : tuple
			range of x
		range_y = (-1,1) : tuple
			range of y

		returns:
		-----------
			plane : pyFish.metrics.Plane
				plane object
		"""
		x = x[~np.isnan(z)]
		y = y[~np.isnan(z)]
		z = z[~np.isnan(z)]
		data = np.array(list(zip(x,y,z)))

		x_, y_ = np.meshgrid(np.arange(range_x[0], range_x[-1], inc_x), np.arange(range_y[0], range_y[-1], inc_y))
		X = x_.flatten()
		Y = y_.flatten()

		if order == 1:
			# best-fit linear plane
			A = np.c_[data[:,0], data[:,1], np.ones(data.shape[0])]
			C,_,_,_ = scipy.linalg.lstsq(A, data[:,2])
			return Plane(coefficients=C, order=order)
		else:
			order = 2
			# best-fit quadratic curve
			A = np.c_[np.ones(data.shape[0]), data[:,:2], np.prod(data[:,:2], axis=1), data[:,:2]**2]
			C,_,_,_ = scipy.linalg.lstsq(A, data[:,2])
			return Plane(coefficients=C, order=order)

	def histogram_3d(self,x,bins = 20, normed = False, color = 'blue', alpha = 1, hold = False, plot_hist=False):
		"""
		Plotting a 3D histogram

		Parameters
		----------

		sample : array_like.		
		    The data to be histogrammed. It must be an (N,2) array or data 
		    that can be converted to such. The rows of the resulting array 
		    are the coordinates of points in a 2 dimensional polytope.

		bins : sequence or int, optional, default: 10.
		    The bin specification:
		    
		    * A sequence of arrays describing the bin edges along each dimension.
		    * The number of bins for each dimension (bins =[binx,biny])
		    * The number of bins for all dimensions (bins = bins).

		normed : bool, optional, default: False.
		    If False, returns the number of samples in each bin. 
		    If True, returns the bin density bin_count / sample_count / bin_volume.

		color: string, matplotlib color arg, default = 'blue'

		alpha: float, optional, default: 1.
		    0.0 transparent through 1.0 opaque

		hold: boolean, optional, default: False

		Returns   
		--------
		H : ndarray.
		    The bidimensional histogram of sample x.

		edges : list.
		    A list of 2 arrays describing the bin edges for each dimension.

		Examples
		--------
		>>> r = np.random.randn(1000,2)
		>>> H, edges = np.histogram3d(r,bins=[10,15])
		"""

		if np.size(bins) == 1:
		    bins = [bins,bins]

		if(len(x) == 2):
		    x = x.T;
		    

		H, edges = np.histogramdd(x, bins, normed = normed)

		H = H.T
		X = np.array(list(np.linspace(min(edges[0]),max(edges[0]),bins[0]))*bins[1])   
		Y = np.sort(list(np.linspace(min(edges[1]),max(edges[1]),bins[1]))*bins[0])    

		dz = np.array([]);

		for i in range(bins[1]):
		    for j in range(bins[0]):
		        dz = np.append(dz, H[i][j])

		Z = np.zeros(bins[0]*bins[1])

		dx = X[1] - X[0]   
		dy = Y[bins[0]] - Y[0]

		if plot_hist:
			if (not hold):
			    fig = plt.figure(dpi = 300)
			    ax = fig.add_subplot(111, projection='3d')
			    colors = plt.cm.jet(dz.flatten()/float(dz.max()))
			    ax.bar3d(X,Y,Z,dx,dy,dz, alpha = alpha, color = colors);
			else:
			    try:
			        ax = plt.gca();
			        colors = plt.cm.jet(dz.flatten()/float(dz.max()))
			        ax.bar3d(X,Y,Z,dx,dy,dz, alpha = alpha, color = colors);
			    except:
			        plt.close(plt.get_fignums()[-1])
			        fig = plt.figure()
			        ax = fig.add_subplot(111, projection='3d')
			        colors = plt.cm.jet(dz.flatten()/float(dz.max()))
			        ax.bar3d(X,Y,Z,dx,dy,dz, alpha = alpha, color = colors);
		        
		        
			plt.xlabel('X');
			plt.ylabel('Y');
		edges = [X,Y];
		H = dz.reshape(bins[0],bins[1]);

		#return H, edges;
		return H, edges, X, Y, Z, dx, dy, dz


class Plane:
	def __init__(self, coefficients, order):
		self.coeff = coefficients
		self.order = order

	def __str__(self):
		str1 = """2D plane\nOrder: {}\nCoeff: {}""".format(self.order,self.coeff)
		return str1

	def __call__(self, x, y):
		if self.order == 1:
			X = x.flatten()
			Y = y.flatten()
			return np.dot(np.c_[X, Y, np.ones(X.shape)], self.coeff).reshape(x.shape)
		elif self.order == 2:
			X = x.flatten()
			Y = y.flatten()
			return np.dot(np.c_[np.ones(X.shape), X, Y, X*Y, X**2, Y**2], self.coeff).reshape(x.shape)
