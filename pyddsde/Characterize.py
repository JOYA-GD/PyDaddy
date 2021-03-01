import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import pickle
import tqdm
import time
import os
from pyddsde.sde import SDE
from pyddsde.analysis import underlying_noise
from pyddsde.analysis import AutoCorrelation
from pyddsde.analysis import gaussian_test
from pyddsde.preprocessing import preprocessing
from pyddsde.metrics import metrics
from pyddsde.output import output
from pyddsde.output import InputError

warnings.filterwarnings("ignore")

__all__ = ['Characterize']


class Main(preprocessing, gaussian_test, AutoCorrelation):
	"""
	main class

    :meta private:
	"""
	def __init__(
			self,
			data,
			t=1,
			dt='auto',
			delta_t=1,
			t_lag=1000,
			inc=0.01,
			inc_x=0.1,
			inc_y=0.1,
			fft=True,
			slider_range=None,
			slider_timescales = None,
			n_trials=1,
			show_summary=True,
			max_order = 15,
			order_metric = 'R2_adj',
			**kwargs):

		self._data = data
		self._t = t
		self.dt_ = dt

		self.t_lag = t_lag
		self.max_order = max_order
		self.inc = inc
		self.inc_x = inc_x
		self.inc_y = inc_y
		self.delta_t = delta_t
		self.order_metric = order_metric
		self.fft = fft
		self.n_trials = n_trials
		self._show_summary = show_summary

		self.drift_order = None
		self.diff_order = None

		self.drift_order = None
		self.diff_order = None

		self.op_range = None
		self.op_x_range = None
		self.op_y_range = None
		self.slider_range = slider_range
		self.slider_timescales = slider_timescales

		# When t_lag is greater than timeseries length, reassign its value as length of data
		if self.t_lag > len(data[0]):
			print('Warning : t_lag is greater that the length of data; setting t_lag as {}\n'.format(len(data[0]) - 1))
			self.t_lag = len(data[0]) - 1

		self.__dict__.update(kwargs)
		preprocessing.__init__(self)
		gaussian_test.__init__(self)
		AutoCorrelation.__init__(self)
		#SDE.__init__(self)

		#if t is None and t_int is None:
		#	raise InputError("Characterize(data, t, t_int)","Missing data. Either 't' ot 't_int' must be given, both cannot be None")

		return None

	def _timestep(self, t):
		return (t[-1]-t[0]) / (len(t)-1)

	def _slider_data(self, Mx, My, save=False, savepath='results'):
		time_scale_list = self._get_slider_timescales(self.slider_range, self.slider_timescales)
		drift_data_dict = dict()
		diff_data_dict = dict()
		for time_scale in tqdm.tqdm(time_scale_list, desc='Generating Slider data'):
			if self.vector:
				avgdriftX, avgdriftY, avgdiffX, avgdiffY, avgdiffXY, op_x, op_y = self._vector_drift_diff(Mx,My,inc_x=self.inc_x,inc_y=self.inc_y,t_int=self.t_int, dt=time_scale, delta_t=time_scale)
				drift_data = [avgdriftX/self.n_trials, avgdriftY/self.n_trials, op_x, op_y]
				diff_data = [avgdiffX/self.n_trials, avgdiffY/self.n_trials, op_x, op_y]
			else:
				_, _, avgdiff, avgdrift, op = self._drift_and_diffusion(Mx, t_int=self.t_int, dt=time_scale, delta_t=time_scale, inc=self.inc)
				drift_data = [avgdrift/self.n_trials, op]
				diff_data = [avgdiff/self.n_trials, op]

			drift_data_dict[time_scale] = drift_data
			diff_data_dict[time_scale] = diff_data

		if save:
			savepath = self._make_directory(os.path.join(savepath, self.res_dir))
			with open(os.path.join(savepath, 'slider_data.pkl'), 'wb') as f:
				pickle.dump([drift_data_dict, diff_data_dict],
							f,
							protocol=pickle.HIGHEST_PROTOCOL)

		return drift_data_dict, diff_data_dict

	def __call__(self, data, t=1, dt='auto', **kwargs):
		self.__dict__.update(kwargs)
		#if t is None and t_int is None:
		#	raise InputError("Either 't' or 't_int' must be given, both cannot be None")
		self._t = t
		if len(data) == 1:
			self._X = np.array(data[0])
			self._M_square = np.array(data[0])
			self.vector = False
		elif len(data) == 2:
			self._Mx, self._My = np.array(data[0]), np.array(data[1])
			self._M_square = self._Mx**2 + self._My**2
			self._X = self._Mx.copy()
			self.vector = True
		else:
			raise InputError('Characterize(data=[Mx,My],...)',
							 'data input must be a list of length 1 or 2!')

		#if t_int is None: self.t_int = self._timestep(t)
		if not hasattr(t, "__len__"):
			self.t_int = t
		else:
			if len(t) != len(self._M_square):
				raise InputError(
					"len(Mx^2 + My^2) == len(t)",
					"TimeSeries and time-stamps must be of same length")
			self.t_int = self._timestep(t)

		#print('opt_dt')
		self.dt = self._optimium_timescale(self._X,
										   self._M_square,
										   t_int=self.t_int,
										   dt=dt,
										   max_order=self.max_order,
										   t_lag=self.t_lag,
										   inc=self.inc)
		if not self.vector:
			self._diff_, self._drift_, self._avgdiff_, self._avgdrift_, self._op_ = self._drift_and_diffusion(
				self._X,
				self.t_int,
				dt=self.dt,
				delta_t=self.delta_t,
				inc=self.inc)
			self._avgdiff_ = self._avgdiff_ / self.n_trials
			self._avgdrift_ = self._avgdrift_ / self.n_trials
			self._drift_slider, self._diff_slider = self._slider_data(self._X, None)
		else:
			#print('drift diff')
			self._avgdriftX_, self._avgdriftY_, self._avgdiffX_, self._avgdiffY_, self._avgdiffXY_, self._op_x_, self._op_y_ = self._vector_drift_diff(
				self._Mx,
				self._My,
				inc_x=self.inc_x,
				inc_y=self.inc_y,
				t_int=self.t_int,
				dt=self.dt,
				delta_t=self.delta_t)
			self._avgdriftX_ = self._avgdriftX_ / self.n_trials
			self._avgdriftY_ = self._avgdriftY_ / self.n_trials
			self._avgdiffX_ = self._avgdiffX_ / self.n_trials
			self._avgdiffY_ = self._avgdiffY_ / self.n_trials
			self._avgdiffXY_ = self._avgdiffXY_ / self.n_trials
			self._drift_slider, self._diff_slider = self._slider_data(
				self._Mx, self._My)

		self.gaussian_noise, self._noise, self._kl_dist, self.k, self.l_lim, self.h_lim, self._noise_correlation = self._noise_analysis(
			self._X, self.dt, self.delta_t, self.t_int, inc=self.inc, point=0)
		#X, dt, delta_t, t_int, inc=0.01, point=0,
		return output(self)


class Characterize(object):
	"""
	Analyse a time series data and get drift and diffusion plots.

	Args
	----
	data : list
		time series data to be analysed, data = [x] for scalar data and data = [x1, x2] for vector
		where x, x1 and x2 are of numpy.array object type
	t : float, array, optional(default=1.0)
		float if its time increment between observation

		numpy.array if time stamp of time series
	dt : int,'auto', optional(default='auto')
		time scale for drift

		if 'auto' time scale is decided based of drift order.
	delta_t : int, optional(default=1)
		time scale for difusion
	inc : float, optional(default=0.01)
		increment in order parameter for scalar data
	inc_x : float, optional(default=0.1)
		increment in order parameter for vector data x1
	inc_y : float, optional(default=0.1)
		increment in order parameter for vector data x2
	fft : bool, optional(default=True)
		if true use fft method to calculate autocorrelation else, use standard method
	slider_range : tuple, optional(default=None)
		range of the slider values, (start, stop, n_steps),
		if None, uses the default range, ie (1, 2*auto_correlation_time, 8)
	slider_timescales : list, optional(default=None)
		List of timescale values to include in slider.
	n_trials : int, optional(default=1)
		Number of trials, concatenated timeseries of multiple trials is used.
	show_summary : bool, optional(default=True)
		print data summary and show summary chart.

	**kwargs 
		all the parameters for inherited methods.

	returns
	-------
	output : pyddsde.output.output
		object to access the analysed data, parameters, plots and save them.
	"""
	def __new__(
			cls,
			data,
			t=1.0,
			dt='auto',
			delta_t=1,
			inc=0.01,
			inc_x=0.1,
			inc_y=0.1,
			slider_range=None,
			slider_timescales=None,
			n_trials=1,
			show_summary=True,
			**kwargs):

		ddsde = Main(
			data=data,
			t=t,
			dt=dt,
			delta_t=delta_t,
			inc=inc,
			inc_x=inc_x,
			inc_y=inc_y,
			slider_range=slider_range,
			slider_timescales=slider_timescales,
			n_trials=n_trials,
			show_summary=show_summary,
			**kwargs)

		return ddsde(data=data, t=t, dt=dt)

