from __future__ import print_function, division, absolute_import
from . import imgaug as ia
from .external.opensimplex import OpenSimplex
from abc import ABCMeta, abstractmethod
import numpy as np
import copy as copy_module
import six
import six.moves as sm
import scipy

@six.add_metaclass(ABCMeta)
class StochasticParameter(object):
    """
    Abstract parent class for all stochastic parameters.

    Stochastic parameters are here all parameters from which values are
    supposed to be sampled. Usually the sampled values are to a degree random.
    E.g. a stochastic parameter may be the range [-10, 10], with sampled
    values being 5.2, -3.7, -9.7 and 6.4.

    """

    def __init__(self):
        super(StochasticParameter, self).__init__()

    def draw_sample(self, random_state=None):
        """
        Draws a single sample value from this parameter.

        Parameters
        ----------
        random_state : None or np.random.RandomState, optional(default=None)
            A random state to use during the sampling process.
            If None, the libraries global random state will be used.

        Returns
        -------
        out : anything
            A single sample value.

        """
        return self.draw_samples(1, random_state=random_state)[0]

    def draw_samples(self, size, random_state=None):
        """
        Draws one or more sample values from the parameter.

        Parameters
        ----------
        size : tuple of int
            Number of sample values by
            dimension.

        random_state : None or np.random.RandomState, optional(default=None)
            A random state to use during the sampling process.
            If None, the libraries global random state will be used.

        Returns
        -------
        out : (size) iterable
            Sampled values. Usually a numpy ndarray of basically any dtype,
            though not strictly limited to numpy arrays.

        """
        random_state = random_state if random_state is not None else ia.current_random_state()
        return self._draw_samples(size, random_state)

    @abstractmethod
    def _draw_samples(self, size, random_state):
        raise NotImplementedError()

    def copy(self):
        """
        Create a shallow copy of this parameter.

        Returns
        -------
        out : StochasticParameter
            Shallow copy.

        """
        return copy_module.copy(self)

    def deepcopy(self):
        """
        Create a deep copy of this parameter.

        Returns
        -------
        out : StochasticParameter
            Deep copy.

        """
        return copy_module.deepcopy(self)

class Binomial(StochasticParameter):
    """
    Binomial distribution.

    Parameters
    ----------
    p : number or StochasticParameter
        Probability of the binomial distribution. Expected to be in the
        range [0, 1]. If this is a StochasticParameter, the value will be
        sampled once per call to _draw_samples().

    Examples
    --------
    >>> param = Binomial(Uniform(0.01, 0.2))

    Uses a varying probability `p` between 0.01 and 0.2 per sampling.

    """

    def __init__(self, p):
        super(Binomial, self).__init__()

        if isinstance(p, StochasticParameter):
            self.p = p
        elif ia.is_single_number(p):
            assert 0 <= p <= 1.0, "Expected probability p to be in range [0.0, 1.0], got %s." % (p,)
            self.p = Deterministic(float(p))
        else:
            raise Exception("Expected StochasticParameter or float/int value, got %s." % (type(p),))

    def _draw_samples(self, size, random_state):
        p = self.p.draw_sample(random_state=random_state)
        assert 0 <= p <= 1.0, "Expected probability p to be in range [0.0, 1.0], got %s." % (p,)
        return random_state.binomial(1, p, size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if isinstance(self.p, float):
            return "Binomial(%.4f)" % (self.p,)
        else:
            return "Binomial(%s)" % (self.p,)

class Choice(StochasticParameter):
    """
    Parameter that samples value from a list of allowed values.

    Parameters
    ----------
    a : iterable
        List of allowed values.
        Usually expected to be integers, floats or strings.

    replace : bool, optional(default=True)
        Whether to perform sampling with or without
        replacing.

    p : None or iterable, optional(default=None)
        Optional probabilities of each element in `a`.
        Must have the same length as `a` (if provided).

    Examples
    --------
    >>> param = Choice([0.25, 0.5, 0.75], p=[0.25, 0.5, 0.25])

    Parameter of which 50 pecent of all sampled values will be 0.5.
    The other 50 percent will be either 0.25 or 0.75.

    """
    def __init__(self, a, replace=True, p=None):
        super(Choice, self).__init__()

        self.a = a
        self.replace = replace
        self.p = p

    def _draw_samples(self, size, random_state):
        return random_state.choice(self.a, size, replace=self.replace, p=self.p)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Choice(a=%s, replace=%s, p=%s)" % (str(self.a), str(self.replace), str(self.p),)

class DiscreteUniform(StochasticParameter):
    """
    Parameter that resembles a discrete range of values [a .. b].

    Parameters
    ----------
    {a, b} : int or StochasticParameter
        Lower and upper bound of the sampling range. Values will be sampled
        from a <= x <= b. All sampled values will be discrete. If a or b is
        a StochasticParameter, it will be queried once per sampling to
        estimate the value of a/b. If a>b, the values will automatically be
        flipped. If a==b, all generated values will be identical to a.

    Examples
    --------
    >>> param = DiscreteUniform(10, Choice([20, 30, 40]))

    Sampled values will be discrete and come from the either [10..20] or
    [10..30] or [10..40].

    """

    def __init__(self, a, b):
        super(DiscreteUniform, self).__init__()

        # for two ints the samples will be from range a <= x <= b
        assert isinstance(a, (int, StochasticParameter)), "Expected a to be int or StochasticParameter, got %s" % (type(a),)
        assert isinstance(b, (int, StochasticParameter)), "Expected b to be int or StochasticParameter, got %s" % (type(b),)

        if ia.is_single_integer(a):
            self.a = Deterministic(a)
        else:
            self.a = a

        if ia.is_single_integer(b):
            self.b = Deterministic(b)
        else:
            self.b = b

    def _draw_samples(self, size, random_state):
        a = self.a.draw_sample(random_state=random_state)
        b = self.b.draw_sample(random_state=random_state)
        if a > b:
            a, b = b, a
        elif a == b:
            return np.tile(np.array([a]), size)
        return random_state.randint(a, b + 1, size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "DiscreteUniform(%s, %s)" % (self.a, self.b)

class Poisson(StochasticParameter):
    """
    Parameter that resembles a poisson distribution.

    A poisson distribution with lambda=0 has its highest probability at
    point 0 and decreases quickly from there.
    Poisson distributions are discrete and never negative.

    Parameters
    ----------
    lam : number or tuple of two number or list of number or StochasticParameter
        Lambda parameter of the poisson
        distribution.
            * If a number, this number will be used as a constant value.
            * If a tuple of two numbers (a, b), the value will be sampled
              once per call to `_draw_samples()` from the range [a, b).
            * If a list of numbers, a random value will be picked from the
              list per call to `_draw_samples()`.
            * If a StochasticParameter, that parameter will be queried once
              per call to `_draw_samples()`.

    Examples
    --------
    >>> param = Poisson(0)

    Sample from a poisson distribution with lambda=0.

    """

    def __init__(self, lam):
        super(Poisson, self).__init__()

        if ia.is_single_number(lam):
            self.lam = Deterministic(lam)
        elif isinstance(lam, tuple):
            assert len(lam) == 2
            self.lam = Uniform(lam[0], lam[1])
        elif ia.is_iterable(lam):
            self.lam = Choice(lam)
        elif isinstance(lam, StochasticParameter):
            self.lam = lam
        else:
            raise Exception("Expected number, tuple of two number, list of number or StochasticParameter for lam, got %s." % (type(lam),))

    def _draw_samples(self, size, random_state):
        lam = self.lam.draw_sample(random_state=random_state)
        lam = max(lam, 0)

        return random_state.poisson(lam=lam, size=size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Poisson(%s)" % (self.lam,)

class Normal(StochasticParameter):
    """
    Parameter that resembles a (continuous) normal distribution.

    This is a wrapper around numpy's random.normal().

    Parameters
    ----------
    loc : number or StochasticParameter
        The mean of the normal distribution.
        If StochasticParameter, the mean will be sampled once per call
        to _draw_samples().

    scale : number or StochasticParameter
        The standard deviation of the normal distribution.
        If StochasticParameter, the scale will be sampled once per call
        to _draw_samples().

    Examples
    --------
    >>> param = Normal(Choice([-1.0, 1.0]), 1.0)

    A standard normal distribution, which's mean is shifted either 1.0 to
    the left or 1.0 to the right.

    """
    def __init__(self, loc, scale):
        super(Normal, self).__init__()

        if isinstance(loc, StochasticParameter):
            self.loc = loc
        elif ia.is_single_number(loc):
            self.loc = Deterministic(loc)
        else:
            raise Exception("Expected float, int or StochasticParameter as loc, got %s, %s." % (type(loc),))

        if isinstance(scale, StochasticParameter):
            self.scale = scale
        elif ia.is_single_number(scale):
            assert scale >= 0, "Expected scale to be in range [0, inf) got %s (type %s)." % (scale, type(scale))
            self.scale = Deterministic(scale)
        else:
            raise Exception("Expected float, int or StochasticParameter as scale, got %s, %s." % (type(scale),))

    def _draw_samples(self, size, random_state):
        loc = self.loc.draw_sample(random_state=random_state)
        scale = self.scale.draw_sample(random_state=random_state)
        assert scale >= 0, "Expected scale to be in rnage [0, inf), got %s." % (scale,)
        if scale == 0:
            return np.tile(loc, size)
        else:
            return random_state.normal(loc, scale, size=size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Normal(loc=%s, scale=%s)" % (self.loc, self.scale)

class Uniform(StochasticParameter):
    """
    Parameter that resembles a (continuous) uniform range [a, b).

    Parameters
    ----------
    {a, b} : number or StochasticParameter
        Lower and upper bound of the sampling range. Values will be sampled
        from a <= x < b. All sampled values will be continuous. If a or b is
        a StochasticParameter, it will be queried once per sampling to
        estimate the value of a/b. If a>b, the values will automatically be
        flipped. If a==b, all generated values will be identical to a.

    Examples
    --------
    >>> param = Uniform(0, 10.0)

    Samples random values from the range [0, 10.0).

    """
    def __init__(self, a, b):
        super(Uniform, self).__init__()

        assert isinstance(a, (int, float, StochasticParameter)), "Expected a to be int, float or StochasticParameter, got %s" % (type(a),)
        assert isinstance(b, (int, float, StochasticParameter)), "Expected b to be int, float or StochasticParameter, got %s" % (type(b),)

        if ia.is_single_number(a):
            self.a = Deterministic(a)
        else:
            self.a = a

        if ia.is_single_number(b):
            self.b = Deterministic(b)
        else:
            self.b = b

    def _draw_samples(self, size, random_state):
        a = self.a.draw_sample(random_state=random_state)
        b = self.b.draw_sample(random_state=random_state)
        if a > b:
            a, b = b, a
        elif a == b:
            return np.tile(np.array([a]), size)
        return random_state.uniform(a, b, size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Uniform(%s, %s)" % (self.a, self.b)

class Beta(StochasticParameter):
    """
    Parameter that resembles a (continuous) beta distribution.

    Parameters
    ----------
    {alpha, beta} : number or tuple of two number or list of number or StochasticParameter
        alpha and beta parameters of the beta
        distribution.
            * If number, that number will always be used.
            * If tuple of two number, a random value will be sampled per
              call to `_draw_samples()` from the range [a, b).
            * If list of number, a random element from that list will be
              sampled per call to `_draw_samples()`.
            * If a StochasticParameter, a random value will be sampled
              from that parameter per call to `_draw_samples()`.
        alpha and beta have to be values above 0. If they end up <=0 they
        are automatically clipped to 0+epsilon.

    epsilon : number
        Clipping parameter. If alpha or beta end up <=0, they are clipped to
        0+epsilon.

    Examples
    --------
    >>> param = Beta(0.5, 0.5)

    Samples random values from the beta distribution with alpha=beta=0.5.

    """
    def __init__(self, alpha, beta, epsilon=0.0001):
        super(Beta, self).__init__()

        def handle_param(param, name):
            if ia.is_single_number(param):
                return Deterministic(param)
            elif isinstance(param, tuple):
                assert len(param) == 2
                return Uniform(param[0], param[1])
            elif ia.is_iterable(param):
                return Choice(param)
            elif isinstance(param, StochasticParameter):
                return param
            else:
                raise Exception("Expected number, tuple of two number, list of number or StochasticParameter for %s, got %s." % (name, type(param),))

        self.alpha = handle_param(alpha, "alpha")
        self.beta = handle_param(beta, "beta")

        assert ia.is_single_number(epsilon)
        self.epsilon = epsilon

    def _draw_samples(self, size, random_state):
        alpha = self.alpha.draw_sample(random_state=random_state)
        beta = self.beta.draw_sample(random_state=random_state)
        alpha = max(alpha, self.epsilon)
        beta = max(beta, self.epsilon)
        return random_state.beta(alpha, beta, size=size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Beta(%s, %s)" % (self.alpha, self.beta)

class Deterministic(StochasticParameter):
    """
    Parameter that resembles a constant value.

    If N values are sampled from this parameter, it will return N times V,
    where V is the constant value.

    Parameters
    ----------
    value : number or string or StochasticParameter
        A constant value to use.
        A string may be provided to generate arrays of strings.
        If this is a StochasticParameter, a single value will be sampled
        from it exactly once and then used as the constant value.

    Examples
    --------
    >>> param = Deterministic(10)

    Will always sample the value 10.

    """
    def __init__(self, value):
        super(Deterministic, self).__init__()

        if isinstance(value, StochasticParameter):
            self.value = value.draw_sample()
        elif ia.is_single_number(value) or ia.is_string(value):
            self.value = value
        else:
            raise Exception("Expected StochasticParameter object or number or string, got %s." % (type(value),))

    def _draw_samples(self, size, random_state):
        return np.tile(np.array([self.value]), size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if ia.is_single_integer(self.value):
            return "Deterministic(int %d)" % (self.value,)
        elif ia.is_single_float(self.value):
            return "Deterministic(float %.8f)" % (self.value,)
        else:
            return "Deterministic(%s)" % (str(self.value),)

class FromLowerResolution(StochasticParameter):
    """
    A meta parameter used to sample other parameter values on a low resolution
    2d plane (where 2d means of size (H,W,C)).

    This is intended to be used with parameters that would usually sample
    once value per pixel (or one value per pixel and channel). With this
    parameter, the sampling can be made more coarse, i.e. the result will
    become rectangles instead of single pixels.

    Parameters
    ----------
    other_param : StochasticParameter
        The other parameter which is to be sampled on a coarser
        image.

    size_percent : None or number or iterable of two numbers or StochasticParameter, optional(default=None)
        Size of the 2d sampling plane in percent of the requested size.
        I.e. this is relative to the size provided in the call to
        `_draw_samples(size, ...)`. Lower values will result in smaller
        sampling planes, which are then upsampled to `size`. This means that
        lower values will result in larger rectangles.
        The size may be provided as a constant value or a tuple (a, b), which
        will automatically be converted to the continuous uniform range [a, b)
        or a StochasticParameter, which will be queried per call to
        `_draw_samples()`.

    size_px : None or number or iterable of two numbers or StochasticParameter, optional(default=None)
        Size of the 2d sampling plane in pixels.
        Lower values will result in smaller sampling planes, which are then
        upsampled to the input `size` of `draw_samples(size, ...)`.
        This means that lower values will result in larger rectangles.
        The size may be provided as a constant value or a tuple (a, b), which
        will automatically be converted to the discrete uniform range [a..b]
        or a StochasticParameter, which will be queried per call to
        `_draw_samples()`.

    method : string or int or StochasticParameter, optional(default="nearest")
        Upsampling/interpolation method to use. This is used after the sampling
        is finished and the low resolution plane has to be upsampled to the
        requested `size` in `_draw_samples(size, ...)`. The method may be
        the same as in `imgaug.imresize_many_images()`. Usually `nearest`
        or `linear` are good choices. `nearest` will result in rectangles
        with sharp edges and `linear` in rectangles with blurry and round
        edges. The method may be provided as a StochasticParameter, which
        will be queried per call to `_draw_samples()`.

    min_size : int, optional(default=1)
        Minimum size in pixels of the low resolution sampling
        plane.

    Examples
    --------
    >>> param = FromLowerResolution(Binomial(0.05), size_px=(2, 16), method=Choice(["nearest", "linear"]))

    Samples from a binomial distribution with p=0.05. The sampling plane
    will always have a size HxWxC with H and W being independently sampled
    from [2..16] (i.e. it may range from 2x2xC up to 16x16xC max, but may
    also be e.g. 4x8xC). The upsampling method will be "nearest" in 50 percent
    of all cases and "linear" in the other 50 percent. The result will
    sometimes be rectangular patches of sharp 1s surrounded by 0s and
    sometimes blurry blobs of 1s, surrounded by values <1.0.

    """
    def __init__(self, other_param, size_percent=None, size_px=None, method="nearest", min_size=1):
        super(StochasticParameter, self).__init__()

        assert size_percent is not None or size_px is not None

        if size_percent is not None:
            self.size_method = "percent"
            self.size_px = None
            if ia.is_single_number(size_percent):
                self.size_percent = Deterministic(size_percent)
            elif ia.is_iterable(size_percent):
                assert len(size_percent) == 2
                self.size_percent = Uniform(size_percent[0], size_percent[1])
            elif isinstance(size_percent, StochasticParameter):
                self.size_percent = size_percent
            else:
                raise Exception("Expected int, float, tuple of two ints/floats or StochasticParameter for size_percent, got %s." % (type(size_percent),))
        else: # = elif size_px is not None:
            self.size_method = "px"
            self.size_percent = None
            if ia.is_single_integer(size_px):
                self.size_px = Deterministic(size_px)
            elif ia.is_iterable(size_px):
                assert len(size_px) == 2
                self.size_px = DiscreteUniform(size_px[0], size_px[1])
            elif isinstance(size_px, StochasticParameter):
                self.size_px = size_px
            else:
                raise Exception("Expected int, float, tuple of two ints/floats or StochasticParameter for size_px, got %s." % (type(size_px),))

        self.other_param = other_param

        if ia.is_string(method) or ia.is_single_integer(method):
            self.method = Deterministic(method)
        elif isinstance(method, StochasticParameter):
            self.method = method
        else:
            raise Exception("Expected string or StochasticParameter, got %s." % (type(method),))

        self.min_size = min_size

    def _draw_samples(self, size, random_state):
        if len(size) == 3:
            n = 1
            h, w, c = size
        elif len(size) == 4:
            n, h, w, c = size
        else:
            raise Exception("FromLowerResolution can only generate samples of shape (H, W, C) or (N, H, W, C), requested was %s." % (str(size),))

        if self.size_method == "percent":
            hw_percents = self.size_percent.draw_samples((n, 2), random_state=random_state)
            hw_pxs = (hw_percents * np.array([h, w])).astype(np.int32)
        else:
            hw_pxs = self.size_px.draw_samples((n, 2), random_state=random_state)

        methods = self.method.draw_samples((n,), random_state=random_state)
        result = None
        #for i, (size_factor, method) in enumerate(zip(size_factors, methods)):
        for i, (hw_px, method) in enumerate(zip(hw_pxs, methods)):
            #h_small = max(int(h * size_factor), self.min_size)
            #w_small = max(int(w * size_factor), self.min_size)
            h_small = max(hw_px[0], self.min_size)
            w_small = max(hw_px[1], self.min_size)
            samples = self.other_param.draw_samples((1, h_small, w_small, c), random_state=random_state)
            samples_upscaled = ia.imresize_many_images(samples, (h, w), interpolation=method)
            if result is None:
                result = np.zeros((n, h, w, c), dtype=samples.dtype)
            result[i] = samples_upscaled

        if len(size) == 3:
            return result[0]
        else:
            return result

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if self.size_method == "percent":
            return "FromLowerResolution(size_percent=%s, method=%s, other_param=%s)" % (self.size_percent, self.method, self.other_param)
        else:
            return "FromLowerResolution(size_px=%s, method=%s, other_param=%s)" % (self.size_px, self.method, self.other_param)

class Clip(StochasticParameter):
    """
    Clips another parameter to a defined value range.

    Parameters
    ----------
    other_param : StochasticParameter
        The other parameter, which's values are to be
        clipped.

    minval : None or number, optional(default=None)
        The minimum value to use.
        If None, no minimum will be used.

    maxval : None or number, optional(default=None)
        The maximum value to use.
        If None, no maximum will be used.

    Examples
    --------
    >>> param = Clip(Normal(0, 1.0), minval=-2.0, maxval=2.0)

    Defines a standard normal distribution, which's values never go below -2.0
    or above 2.0. Note that this will lead to small "bumps" of higher
    probability at -2.0 and 2.0, as values below/above these will be clipped
    to them.

    """
    def __init__(self, other_param, minval=None, maxval=None):
        super(Clip, self).__init__()

        assert isinstance(other_param, StochasticParameter)
        assert minval is None or ia.is_single_number(minval)
        assert maxval is None or ia.is_single_number(maxval)

        self.other_param = other_param
        self.minval = minval
        self.maxval = maxval

    def _draw_samples(self, size, random_state):
        samples = self.other_param.draw_samples(size, random_state=random_state)
        if self.minval is not None and self.maxval is not None:
            np.clip(samples, self.minval, self.maxval, out=samples)
        elif self.minval is not None:
            np.clip(samples, self.minval, np.max(samples), out=samples)
        elif self.maxval is not None:
            np.clip(samples, np.min(samples), self.maxval, out=samples)
        else:
            pass
        return samples

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        opstr = str(self.other_param)
        if self.minval is not None and self.maxval is not None:
            return "Clip(%s, %.6f, %.6f)" % (opstr, float(self.minval), float(self.maxval))
        elif self.minval is not None:
            return "Clip(%s, %.6f, None)" % (opstr, float(self.minval))
        elif self.maxval is not None:
            return "Clip(%s, None, %.6f)" % (opstr, float(self.maxval))
        else:
            return "Clip(%s, None, None)" % (opstr,)

class Multiply(StochasticParameter):
    """
    Parameter to multiply other parameter's results with.

    Parameters
    ----------
    other_param : StochasticParameter
        Other parameter which's sampled values are to be
        multiplied.

    val : number
        Multiplier to
        use.

    Examples
    --------
    >>> param = Multiply(Uniform(0.0, 1.0), -1)

    Converts a uniform range [0.0, 1.0) to (-1.0, 0.0].

    """
    def __init__(self, other_param, val):
        super(Multiply, self).__init__()

        assert isinstance(other_param, StochasticParameter)
        assert ia.is_single_number(val)

        self.other_param = other_param
        self.val = val

    def _draw_samples(self, size, random_state):
        samples = self.other_param.draw_samples(size, random_state=random_state)
        return samples * self.val

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        opstr = str(self.other_param)
        return "Multiply(%s, %s)" % (opstr, str(self.val))

# TODO this always aggregates the result in high resolution space,
# instead of aggregating them in low resolution and then only upscaling the
# final image (for N iterations that would save up to N-1 upscales)
class IterativeNoiseAggregator(StochasticParameter):
    """
    Parameter to generate noise maps in multiple iterations and aggregate
    their results.

    This is supposed to be used in conjunction with SimplexNoise or
    FrequencyNoise.

    Parameters
    ----------
    other_param : StochasticParameter
        The noise parameter to iterate multiple
        times.

    iterations : int or iterable of two ints or list of ints or StochasticParameter, optional(default=(1, 3))
        The number of iterations. This may be a single integer or a tuple
        of integers (a, b), which will result in [a..b] iterations or
        a list of integers [a, b, c, ...], which will result in a or b or
        c, ... iterations. It may also be a StochasticParameter, in which case
        the number of iterations will be sampled once per call
        to `_draw_samples()`.

    aggregation_method : ia.ALL or string or list of string or StochasticParameter, optional(default=["max", "avg"])
        The method to use to aggregate the results of multiple iterations.
        If a string, it must have the value "min" or "max" or "avg".
        If "min" is chosen, the elementwise minimum will be computed over
        all iterations (pushing the noise towards zeros). "max" will result
        in the elementwise maximum and "avg" in the average over all
        iterations. If `ia.ALL` is used, it will be randomly either min or max
        or avg (per call to `_draw_samples()`). If a list is chosen, it must
        contain the mentioned strings and a random one will be picked per call
        to `_draw_samples()`. If a StochasticParameter is used, a value will
        be sampled from it per call to `_draw_samples()`.

    Examples
    --------
    >>> noise = IterativeNoiseAggregator(SimplexNoise(), iterations=(2, 5), aggregation_method="max")

    Generates per call 2 to 5 times simplex noise of a given size. Then
    combines these noise maps to a single map using elementwise maximum.

    """
    def __init__(self, other_param, iterations=(1, 3), aggregation_method=["max", "avg"]):
        assert isinstance(other_param, StochasticParameter)
        self.other_param = other_param

        if ia.is_single_integer(iterations):
            assert 1 <= iterations <= 1000
            self.iterations = Deterministic(iterations)
        elif ia.is_iterable(iterations):
            assert len(iterations) == 2
            assert all([ia.is_single_integer(val) for val in iterations])
            assert all([1 <= val <= 10000 for val in iterations])
            self.iterations = DiscreteUniform(iterations[0], iterations[1])
        elif isinstance(iterations, list):
            assert len(iterations) > 0
            assert all([1 <= val <= 10000 for val in iterations])
            self.iterations = Choice(iterations)
        elif isinstance(iterations, StochasticParameter):
            self.iterations = iterations
        else:
            raise Exception("Expected iterations to be int or tuple of two ints or StochasticParameter, got %s." % (type(iterations),))

        if aggregation_method == ia.ALL:
            self.aggregation_method = Choice(["min", "max", "avg"])
        elif ia.is_string(aggregation_method):
            self.aggregation_method = Deterministic(aggregation_method)
        elif isinstance(aggregation_method, list):
            assert len(aggregation_method) >= 1
            assert all([ia.is_string(val) for val in aggregation_method])
            self.aggregation_method = Choice(aggregation_method)
        elif isinstance(aggregation_method, StochasticParameter):
            self.aggregation_method = aggregation_method
        else:
            raise Exception("Expected aggregation_method to be string or list of strings or StochasticParameter, got %s." % (type(aggregation_method),))

    def _draw_samples(self, size, random_state):
        assert len(size) == 2, "Expected requested other_param to have shape (H, W), got shape %s." % (size,)
        h, w = size

        seed = random_state.randint(0, 10**6)
        aggregation_method = self.aggregation_method.draw_sample(random_state=ia.new_random_state(seed))
        iterations = self.iterations.draw_sample(random_state=ia.new_random_state(seed+1))
        assert iterations > 0

        result = np.zeros((h, w), dtype=np.float32)
        for i in sm.xrange(iterations):
            noise_iter = self.other_param.draw_samples((h, w), random_state=ia.new_random_state(seed+2+i))
            if aggregation_method == "avg":
                result += noise_iter
            elif aggregation_method == "min":
                if i == 0:
                    result = noise_iter
                else:
                    result = np.minimum(result, noise_iter)
            else: # self.aggregation_method == "max"
                if i == 0:
                    result = noise_iter
                else:
                    result = np.maximum(result, noise_iter)

        if aggregation_method == "avg":
            result = result / iterations

        return result

class Sigmoid(StochasticParameter):
    """
    Applies a sigmoid function to the outputs of another parameter.

    This is intended to be used in combination with SimplexNoise or
    FrequencyNoise. It pushes the noise values away from ~0.5 and towards
    0.0 or 1.0, making the noise maps more binary.

    Parameters
    ----------
    other_param : StochasticParameter
        The other parameter to which the sigmoid will be
        applied.

    threshold : number or tuple of two numbers or iterable of numbers or StochasticParameter, optional(default=(-10, 10))
        Sets the value of the sigmoid's saddle point, i.e. where values
        start to quickly shift from 0.0 to 1.0.
        This may be set using a single number, a tuple (a, b) (will result in
        a random threshold a<=x<b per call), a list of numbers (will
        result in a random threshold drawn from the list per call) or a
        StochasticParameter (will be queried once per call to determine the
        threshold).

    activated : bool or number, optional(default=True)
        Defines whether the sigmoid is activated. If this is False, the
        results of other_param will not be altered. This may be set to a
        float value p with 0<=p<=1.0, which will result in `activated` being
        True in p percent of all calls.

    mul : number, optional(default=1)
        The results of other_param will be multiplied with this value before
        applying the sigmoid. For noise values (range [0.0, 1.0]) this should
        be set to about 20.

    add : number, optional(default=0)
        This value will be added to the results of other_param before applying
        the sigmoid. For noise values (range [0.0, 1.0]) this should be set
        to about -10.0, provided `mul` was set to 20.

    Examples
    --------
    >>> param = Sigmoid(SimplexNoise(), activated=0.5, mul=20, add=-10)

    Applies a sigmoid to simplex noise in 50 percent of all calls. The noise
    results are modified to match the sigmoid's expected value range. The
    sigmoid's outputs are in the range [0.0, 1.0].

    """
    def __init__(self, other_param, threshold=(-10, 10), activated=True, mul=1, add=0):
        assert isinstance(other_param, StochasticParameter)
        self.other_param = other_param

        if ia.is_single_number(threshold):
            self.threshold = Deterministic(threshold)
        elif isinstance(threshold, tuple):
            assert len(threshold) == 2
            assert all([ia.is_single_number(val) for val in threshold])
            self.threshold = Uniform(threshold[0], threshold[1])
        elif ia.is_iterable(threshold):
            assert len(threshold) > 0
            self.threshold = Choice(threshold)
        elif isinstance(threshold, StochasticParameter):
            self.threshold = threshold
        else:
            raise Exception("Expected threshold to be number or tuple of two numbers or StochasticParameter, got %s." % (type(threshold),))

        if activated in [True, False, 0, 1, 0.0, 1.0]:
            self.activated = Deterministic(int(activated))
        elif ia.is_single_number(activated):
            assert 0 <= activated <= 1.0
            self.activated = Binomial(activated)
        else:
            raise Exception("Expected activated to be boolean or number or StochasticParameter, got %s." % (type(activated),))

        assert ia.is_single_number(mul)
        assert mul > 0
        self.mul = mul

        assert ia.is_single_number(add)
        self.add = add

    @staticmethod
    def create_for_noise(other_param, threshold=(-10, 10), activated=True):
        """
        Creates a Sigmoid that is adjusted to be used with noise parameters,
        i.e. with parameters which's output values are in the range [0.0, 1.0].

        Parameters
        ----------
        other_param : StochasticParameter
            See `Sigmoid`.

        threshold : number or tuple of two numbers or iterable of numbers or StochasticParameter, optional(default=(-10, 10))
            See `Sigmoid`.

        activated : bool or number, optional(default=True)
            See `Sigmoid`.

        Returns
        -------
        out : Sigmoid
            A sigmoid adjusted to be used with noise.

        """
        return Sigmoid(other_param, threshold, activated, mul=20, add=-10)

    def _draw_samples(self, size, random_state):
        seed = random_state.randint(0, 10**6)
        result = self.other_param.draw_samples(size, random_state=ia.new_random_state(seed))
        activated = self.activated.draw_sample(random_state=ia.new_random_state(seed+1))
        threshold = self.threshold.draw_sample(random_state=ia.new_random_state(seed+2))
        if activated > 0.5:
            # threshold must be subtracted here, not added
            # higher threshold = move threshold of sigmoid towards the right
            #                  = make it harder to pass the threshold
            #                  = more 0.0s / less 1.0s
            # by subtracting a high value, it moves each x towards the left,
            # leading to more values being left of the threshold, leading
            # to more 0.0s
            return 1 / (1 + np.exp(-(result * self.mul + self.add - threshold)))
        else:
            return result

"""
class SimplexNoise(StochasticParameter):
    def __init__(self, iterations=(1, 3), size_px_max=(2, 16), upscale_method=["linear", "nearest"], aggregation_method=["max", "avg"], sigmoid=0.5, sigmoid_thresh=(-10, 10)):
        if ia.is_single_integer(iterations):
            assert 1 <= iterations <= 1000
            self.iterations = Deterministic(iterations)
        elif ia.is_iterable(iterations):
            assert len(iterations) == 2
            assert all([ia.is_single_integer(val) for val in iterations])
            assert all([1 <= val <= 10000 for val in iterations])
            self.iterations = DiscreteUniform(iterations[0], iterations[1])
        elif ia.is_iterable(iterations):
            assert len(iterations) > 0
            assert all([1 <= val <= 10000 for val in iterations])
            self.iterations = Choice(iterations)
        elif isinstance(iterations, StochasticParameter):
            self.iterations = iterations
        else:
            raise Exception("Expected iterations to be int or tuple of two ints or StochasticParameter, got %s." % (type(iterations),))

        if ia.is_single_integer(size_px_max):
            assert 1 <= size_px_max <= 10000
            self.size_px_max = Deterministic(size_px_max)
        elif isinstance(size_px_max, tuple):
            assert len(size_px_max) == 2
            assert all([ia.is_single_integer(val) for val in size_px_max])
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = DiscreteUniform(size_px_max[0], size_px_max[1])
        elif ia.is_iterable(size_px_max):
            assert len(size_px_max) > 0
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = Choice(size_px_max)
        elif isinstance(size_px_max, StochasticParameter):
            self.size_px_max = size_px_max
        else:
            raise Exception("Expected size_px_max to be int or tuple of two ints or StochasticParameter, got %s." % (type(size_px_max),))

        if upscale_method == ia.ALL:
            self.upscale_method = Choice(["nearest", "linear", "area", "cubic"])
        elif ia.is_string(upscale_method):
            self.upscale_method = Deterministic(upscale_method)
        elif isinstance(upscale_method, list):
            assert len(upscale_method) >= 1
            assert all([ia.is_string(val) for val in upscale_method])
            self.upscale_method = Choice(upscale_method)
        elif isinstance(upscale_method, StochasticParameter):
            self.upscale_method = upscale_method
        else:
            raise Exception("Expected upscale_method to be string or list of strings or StochasticParameter, got %s." % (type(upscale_method),))

        if aggregation_method == ia.ALL:
            self.aggregation_method = Choice(["min", "max", "avg"])
        elif ia.is_string(aggregation_method):
            self.aggregation_method = Deterministic(aggregation_method)
        elif isinstance(aggregation_method, list):
            assert len(aggregation_method) >= 1
            assert all([ia.is_string(val) for val in aggregation_method])
            self.aggregation_method = Choice(aggregation_method)
        elif isinstance(aggregation_method, StochasticParameter):
            self.aggregation_method = aggregation_method
        else:
            raise Exception("Expected aggregation_method to be string or list of strings or StochasticParameter, got %s." % (type(aggregation_method),))

        if sigmoid in [True, False, 0, 1, 0.0, 1.0]:
            self.sigmoid = Deterministic(int(sigmoid))
        elif ia.is_single_number(sigmoid):
            assert 0 <= sigmoid <= 1.0
            self.sigmoid = Binomial(sigmoid)
        else:
            raise Exception("Expected sigmoid to be boolean or number or StochasticParameter, got %s." % (type(sigmoid),))

        if ia.is_single_number(sigmoid_thresh):
            self.sigmoid_thresh = Deterministic(sigmoid_thresh)
        elif isinstance(sigmoid_thresh, tuple):
            assert len(sigmoid_thresh) == 2
            assert all([ia.is_single_number(val) for val in sigmoid_thresh])
            self.sigmoid_thresh = Uniform(sigmoid_thresh[0], sigmoid_thresh[1])
        elif ia.is_iterable(sigmoid_thresh):
            assert len(sigmoid_thresh) > 0
            self.sigmoid_thresh = Choice(sigmoid_thresh)
        elif isinstance(sigmoid_thresh, StochasticParameter):
            self.sigmoid_thresh = sigmoid_thresh
        else:
            raise Exception("Expected sigmoid_thresh to be number or tuple of two numbers or StochasticParameter, got %s." % (type(sigmoid_thresh),))

    def _draw_samples(self, size, random_state):
        assert len(size) == 2, "Expected requested noise to have shape (H, W), got shape %s." % (size,)
        h, w = size
        seed = random_state.randint(0, 10**6)
        aggregation_method = self.aggregation_method.draw_sample(random_state=ia.new_random_state(seed))
        iterations = self.iterations.draw_sample(random_state=ia.new_random_state(seed+1))
        upscale_methods = self.upscale_method.draw_samples((iterations,), random_state=ia.new_random_state(seed+2))
        result = np.zeros((h, w), dtype=np.float32)
        for i in sm.xrange(iterations):
            noise_iter = self._draw_samples_iteration(h, w, seed + 10 + i, upscale_methods[i])
            if aggregation_method == "avg":
                result += noise_iter
            elif aggregation_method == "min":
                if i == 0:
                    result = noise_iter
                else:
                    result = np.minimum(result, noise_iter)
            else: # self.aggregation_method == "max"
                if i == 0:
                    result = noise_iter
                else:
                    result = np.maximum(result, noise_iter)

        if aggregation_method == "avg":
            result = result / iterations

        sigmoid = self.sigmoid.draw_sample(random_state=ia.new_random_state(seed+3))
        sigmoid_thresh = self.sigmoid_thresh.draw_sample(random_state=ia.new_random_state(seed+4))
        if sigmoid > 0.5:
            # yes, threshold must be subtracted here, not added
            # higher threshold = move threshold of sigmoid towards the right
            #                  = make it harder to pass the threshold
            #                  = more 0.0s / less 1.0s
            # by subtracting a high value, it moves each x towards the left,
            # leading to more values being left of the threshold, leading
            # to more 0.0s
            result = 1 / (1 + np.exp(-(result * 20 - 10 - sigmoid_thresh)))

        #from scipy import misc
        #misc.imshow((result * 255).astype(np.uint8))

        return result

    def _draw_samples_iteration(self, h, w, seed, upscale_method):
        maxlen = max(h, w)
        size_px_max = self.size_px_max.draw_sample(random_state=ia.new_random_state(seed))
        if maxlen > size_px_max:
            downscale_factor = size_px_max / maxlen
            h_small = int(h * downscale_factor)
            w_small = int(w * downscale_factor)
        else:
            h_small = h
            w_small = w

        # don't go below Hx1 or 1xW
        h_small = max(h_small, 1)
        w_small = max(w_small, 1)

        generator = OpenSimplex(seed=seed)
        noise = np.zeros((h_small, w_small), dtype=np.float32)
        for y in sm.xrange(h_small):
            for x in sm.xrange(w_small):
                noise[y, x] = generator.noise2d(y=y, x=x)
        noise_0to1 = (noise + 0.5) / 2

        if noise_0to1.shape != (h, w):
            noise_0to1_uint8 = (noise_0to1 * 255).astype(np.uint8)
            noise_0to1_3d = np.tile(noise_0to1_uint8[..., np.newaxis], (1, 1, 3))
            noise_0to1 = ia.imresize_single_image(noise_0to1_3d, (h, w), interpolation=upscale_method)
            noise_0to1 = (noise_0to1[..., 0] / 255.0).astype(np.float32)

        #from scipy import misc
        #print(noise_0to1.shape, h_small, w_small, self.size_percent, self.size_px_max, maxlen)
        #misc.imshow((noise_0to1 * 255).astype(np.uint8))

        return noise_0to1

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "SimplexNoise(%s, %s, %s, %s, %s, %s, %s)" % (
            str(self.iterations),
            str(self.size_px_max),
            str(self.upscale_method),
            str(self.aggregation_method),
            str(self.sigmoid),
            str(self.sigmoid_thresh)
        )
"""

class SimplexNoise(StochasticParameter):
    """
    A parameter that generates simplex noise of varying resolutions.

    This parameter expects to sample noise for 2d planes, i.e. for
    sizes (H, W) and will return a value in the range [0.0, 1.0] per location
    in that plane.

    The noise is sampled from low resolution planes and
    upscaled to the requested height and width. The size of the low
    resolution plane may be defined (high values can be slow) and the
    interpolation method for upscaling can be set.

    Parameters
    ----------
    size_px_max : int or tuple of two int or list of int or StochasticParameter, optional(default=(2, 16))
        Size in pixels of the low resolution plane.
        A single int will be used as a constant value. A tuple of two
        ints (a, b) will result in random values sampled from [a..b].
        A list of ints will result in random values being sampled from that
        list. A StochasticParameter will be queried once per call
        to `_draw_samples()`.

    upscale_method : string or int or StochasticParameter, optional(default="nearest")
        Upsampling/interpolation method to use. This is used after the sampling
        is finished and the low resolution plane has to be upsampled to the
        requested `size` in `_draw_samples(size, ...)`. The method may be
        the same as in `imgaug.imresize_many_images()`. Usually `nearest`
        or `linear` are good choices. `nearest` will result in rectangles
        with sharp edges and `linear` in rectangles with blurry and round
        edges. The method may be provided as a StochasticParameter, which
        will be queried per call to `_draw_samples()`.

    Examples
    --------
    >>> param = SimplexNoise(upscale_method="linear")

    Results in smooth simplex noise of varying sizes.

    >>> param = SimplexNoise(size_px_max=(8, 16), upscale_method="nearest")

    Results in rectangular simplex noise of rather high detail.

    """
    def __init__(self, size_px_max=(2, 16), upscale_method=["linear", "nearest"]):
        if ia.is_single_integer(size_px_max):
            assert 1 <= size_px_max <= 10000
            self.size_px_max = Deterministic(size_px_max)
        elif isinstance(size_px_max, tuple):
            assert len(size_px_max) == 2
            assert all([ia.is_single_integer(val) for val in size_px_max])
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = DiscreteUniform(size_px_max[0], size_px_max[1])
        elif ia.is_iterable(size_px_max):
            assert len(size_px_max) > 0
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = Choice(size_px_max)
        elif isinstance(size_px_max, StochasticParameter):
            self.size_px_max = size_px_max
        else:
            raise Exception("Expected size_px_max to be int or tuple of two ints or StochasticParameter, got %s." % (type(size_px_max),))

        if upscale_method == ia.ALL:
            self.upscale_method = Choice(["nearest", "linear", "area", "cubic"])
        elif ia.is_string(upscale_method):
            self.upscale_method = Deterministic(upscale_method)
        elif isinstance(upscale_method, list):
            assert len(upscale_method) >= 1
            assert all([ia.is_string(val) for val in upscale_method])
            self.upscale_method = Choice(upscale_method)
        elif isinstance(upscale_method, StochasticParameter):
            self.upscale_method = upscale_method
        else:
            raise Exception("Expected upscale_method to be string or list of strings or StochasticParameter, got %s." % (type(upscale_method),))

    def _draw_samples(self, size, random_state):
        assert len(size) == 2, "Expected requested noise to have shape (H, W), got shape %s." % (size,)
        h, w = size
        seed = random_state.randint(0, 10**6)
        iterations = 1
        aggregation_method = "max"
        upscale_methods = self.upscale_method.draw_samples((iterations,), random_state=ia.new_random_state(seed))
        result = np.zeros((h, w), dtype=np.float32)
        for i in sm.xrange(iterations):
            noise_iter = self._draw_samples_iteration(h, w, seed + 10 + i, upscale_methods[i])
            if aggregation_method == "avg":
                result += noise_iter
            elif aggregation_method == "min":
                if i == 0:
                    result = noise_iter
                else:
                    result = np.minimum(result, noise_iter)
            else: # self.aggregation_method == "max"
                if i == 0:
                    result = noise_iter
                else:
                    result = np.maximum(result, noise_iter)

        if aggregation_method == "avg":
            result = result / iterations

        return result

    def _draw_samples_iteration(self, h, w, seed, upscale_method):
        maxlen = max(h, w)
        size_px_max = self.size_px_max.draw_sample(random_state=ia.new_random_state(seed))
        if maxlen > size_px_max:
            downscale_factor = size_px_max / maxlen
            h_small = int(h * downscale_factor)
            w_small = int(w * downscale_factor)
        else:
            h_small = h
            w_small = w

        # don't go below Hx1 or 1xW
        h_small = max(h_small, 1)
        w_small = max(w_small, 1)

        generator = OpenSimplex(seed=seed)
        noise = np.zeros((h_small, w_small), dtype=np.float32)
        for y in sm.xrange(h_small):
            for x in sm.xrange(w_small):
                noise[y, x] = generator.noise2d(y=y, x=x)
        noise_0to1 = (noise + 0.5) / 2

        if noise_0to1.shape != (h, w):
            noise_0to1_uint8 = (noise_0to1 * 255).astype(np.uint8)
            noise_0to1_3d = np.tile(noise_0to1_uint8[..., np.newaxis], (1, 1, 3))
            noise_0to1 = ia.imresize_single_image(noise_0to1_3d, (h, w), interpolation=upscale_method)
            noise_0to1 = (noise_0to1[..., 0] / 255.0).astype(np.float32)

        #from scipy import misc
        #print(noise_0to1.shape, h_small, w_small, self.size_percent, self.size_px_max, maxlen)
        #misc.imshow((noise_0to1 * 255).astype(np.uint8))

        return noise_0to1

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "SimplexNoise(%s, %s)" % (
            str(self.size_px_max),
            str(self.upscale_method)
        )

class FrequencyNoise(StochasticParameter):
    """
    Parameter to generate noise of varying frequencies.

    This parameter expects to sample noise for 2d planes, i.e. for
    sizes (H, W) and will return a value in the range [0.0, 1.0] per location
    in that plane.

    The exponent controls the frequencies and therefore noise patterns.
    Low values (around -4.0) will result in large blobs. High values (around
    4.0) will result in small, repetitive patterns.

    The noise is sampled from low resolution planes and
    upscaled to the requested height and width. The size of the low
    resolution plane may be defined (high values can be slow) and the
    interpolation method for upscaling can be set.

    Parameters
    ----------
    exponent : number or tuple of numbers of list of numbers or StochasticParameter, optional(default=(-4, 4))
        Exponent to use when scaling in the frequency domain.
        Sane values are in the range -4 (large blobs) to 4 (small patterns).
        To generate cloud-like structures, use roughly -2.
            * If number, then that number will be used as the exponent for all
              iterations.
            * If tuple of two numbers (a, b), then a value will be sampled
              per iteration from the range [a, b].
            * If a list of numbers, then a value will be picked per iteration
              at random from that list.
            * If a StochasticParameter, then a value will be sampled from
              that parameter per iteration.

    size_px_max : int or tuple of ints or list of ints or StochasticParameter, optional(default=(4, 16))
        The frequency noise is generated in a low resolution environment.
        This parameter defines the maximum size of that environment (in
        pixels). The environment is initialized at the same size as the input
        image and then downscaled, so that no side exceeds `size_px_max`
        (aspect ratio is kept).
            * If int, then that number will be used as the size for all
              iterations.
            * If tuple of two ints (a, b), then a value will be sampled
              per iteration from the discrete range [a..b].
            * If a list of ints, then a value will be picked per iteration at
              random from that list.
            * If a StochasticParameter, then a value will be sampled from
              that parameter per iteration.

    upscale_method : None or ia.ALL or string or list of string or StochasticParameter, optional(default=None)
        After generating the noise maps in low resolution environments, they
        have to be upscaled to the input image size. This parameter controls
        the upscaling method.
            * If None, then either 'nearest' or 'linear' or 'cubic' is picked.
              Most weight is put on linear, followed by cubic.
            * If ia.ALL, then either 'nearest' or 'linear' or 'area' or 'cubic'
              is picked per iteration (all same probability).
            * If string, then that value will be used as the method (must be
              'nearest' or 'linear' or 'area' or 'cubic').
            * If list of string, then a random value will be picked from that
              list per iteration.
            * If StochasticParameter, then a random value will be sampled
              from that parameter per iteration.

    Examples
    --------
    >>> param = FrequencyNoise(exponent=-2, size_px_max=(16, 32), upscale_method="linear")

    Generates noise with cloud-like patterns.

    """
    def __init__(self, exponent=(-4, 4), size_px_max=(4, 32), upscale_method=["linear", "nearest"]):
        if ia.is_single_number(exponent):
            self.exponent = Deterministic(exponent)
        elif isinstance(exponent, tuple):
            assert len(exponent) == 2
            assert all([ia.is_single_number(val) for val in exponent])
            self.exponent = Uniform(exponent[0], exponent[1])
        elif ia.is_iterable(exponent):
            assert len(exponent) > 0
            self.exponent = Choice(exponent)
        elif isinstance(exponent, StochasticParameter):
            self.exponent = exponent
        else:
            raise Exception("Expected exponent to be number or tuple of two numbers or StochasticParameter, got %s." % (type(exponent),))

        if ia.is_single_integer(size_px_max):
            assert 1 <= size_px_max <= 10000
            self.size_px_max = Deterministic(size_px_max)
        elif isinstance(size_px_max, tuple):
            assert len(size_px_max) == 2
            assert all([ia.is_single_integer(val) for val in size_px_max])
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = DiscreteUniform(size_px_max[0], size_px_max[1])
        elif ia.is_iterable(sigmoid_thresh):
            assert len(size_px_max) > 0
            assert all([1 <= val <= 10000 for val in size_px_max])
            self.size_px_max = Choice(size_px_max)
        elif isinstance(size_px_max, StochasticParameter):
            self.size_px_max = size_px_max
        else:
            raise Exception("Expected size_px_max to be int or tuple of two ints or StochasticParameter, got %s." % (type(size_px_max),))

        if upscale_method == ia.ALL:
            self.upscale_method = Choice(["nearest", "linear", "area", "cubic"])
        elif ia.is_string(upscale_method):
            self.upscale_method = Deterministic(upscale_method)
        elif isinstance(upscale_method, list):
            assert len(upscale_method) >= 1
            assert all([ia.is_string(val) for val in upscale_method])
            self.upscale_method = Choice(upscale_method)
        elif isinstance(upscale_method, StochasticParameter):
            self.upscale_method = upscale_method
        else:
            raise Exception("Expected upscale_method to be string or list of strings or StochasticParameter, got %s." % (type(upscale_method),))

    def _draw_samples(self, size, random_state):
        # code here is similar to:
        #   http://www.redblobgames.com/articles/noise/2d/
        #   http://www.redblobgames.com/articles/noise/2d/2d-noise.js

        assert len(size) == 2, "Expected requested noise to have shape (H, W), got shape %s." % (size,)

        seed = random_state.randint(0, 10**6)

        h, w = size
        maxlen = max(h, w)
        size_px_max = self.size_px_max.draw_sample(random_state=ia.new_random_state(seed))
        if maxlen > size_px_max:
            downscale_factor = size_px_max / maxlen
            h_small = int(h * downscale_factor)
            w_small = int(w * downscale_factor)
        else:
            h_small = h
            w_small = w

        # don't go below Hx4 or 4xW
        h_small = max(h_small, 4)
        w_small = max(w_small, 4)

        # generate random base matrix
        wn_r = ia.new_random_state(seed+1).rand(h_small, w_small)
        wn_a = ia.new_random_state(seed+2).rand(h_small, w_small)

        wn_r = wn_r * (max(h_small, w_small) ** 2)
        wn_a = wn_a * 2 * np.pi

        wn_r = wn_r * np.cos(wn_a)
        wn_a = wn_r * np.sin(wn_a)

        # pronounce some frequencies
        exponent = self.exponent.draw_sample(random_state=ia.new_random_state(seed+3))
        # this has some similarity with a distance map from the center, but looks a bit more like a cross
        f = self._create_distance_matrix((h_small, w_small))
        f[0, 0] = 1 # necessary to prevent -inf from appearing
        scale = f ** exponent
        scale[0, 0] = 0
        tr = wn_r * scale
        ti = wn_a * scale

        """
        Fmin = 1
        Fmax = 64
        tr = np.zeros(wn_r.shape, dtype=np.float32)
        ti = np.zeros(wn_r.shape, dtype=np.float32)
        for i in range(h_small):
            for j in range(w_small):
                if i==0 and j==0:
                    continue
                f1 = min(i, h_small-i)
                f2 = min(j, w_small-j)
                f = np.sqrt(f1**2 + f2**2)
                #scale = (Fmin <= f <= Fmax) * (f**(2*-2))
                scale = (f**(2*-2))
                x = wn_r[i, j] * scale
                y = wn_a[i, j] * scale
                tr[i, j] = x
                ti[i, j] = y
        """

        wn_freqs_mul = np.zeros(tr.shape, dtype=np.complex)
        wn_freqs_mul.real = tr
        wn_freqs_mul.imag = ti

        wn_inv = np.fft.ifft2(wn_freqs_mul).real

        # normalize to 0 to 1
        wn_inv_min = np.min(wn_inv)
        wn_inv_max = np.max(wn_inv)
        noise_0to1 = (wn_inv - wn_inv_min) / (wn_inv_max - wn_inv_min)

        # upscale from low resolution to image size
        upscale_method = self.upscale_method.draw_sample(random_state=ia.new_random_state(seed+1))
        if noise_0to1.shape != (size[0], size[1]):
            noise_0to1_uint8 = (noise_0to1 * 255).astype(np.uint8)
            noise_0to1_3d = np.tile(noise_0to1_uint8[..., np.newaxis], (1, 1, 3))
            noise_0to1 = ia.imresize_single_image(noise_0to1_3d, (size[0], size[1]), interpolation=upscale_method)
            noise_0to1 = (noise_0to1[..., 0] / 255.0).astype(np.float32)

        return noise_0to1

    def _create_distance_matrix(self, size):
        h, w = size
        def freq(yy, xx):
            f1 = np.minimum(yy, h-yy)
            f2 = np.minimum(xx, w-xx)
            return np.sqrt(f1**2 + f2**2)
        return scipy.fromfunction(freq, (h, w))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "FrequencyNoise(%s, %s, %s)" % (
            str(self.exponent),
            str(self.size_px_max),
            str(self.upscale_method)
        )
