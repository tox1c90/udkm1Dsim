#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2020 Daniel Schick
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

"""A :mod:`Xray` module """

__all__ = ["Xray"]

__docformat__ = "restructuredtext"

import numpy as np
from .simulation import Simulation
from . import u, Q_
from .helpers import make_hash_md5


class Xray(Simulation):
    """Xray

    Base class for all xray simulatuons.

    Args:
        S (object): sample to do simulations with
        force_recalc (boolean): force recalculation of results

    Attributes:
        polarizations (dict): polarization states and according names
        pol_in_state (int): incoming polarization state as defined in polarizations dict
        pol_out_state (int): outgoing polarization state as defined in polarizations dict
        pol_in (float): incoming polarization factor (can be a complex ndarray)
        pol_out (float): outgoing polarization factor (can be a complex ndarray)

    """

    def __init__(self, S, force_recalc, **kwargs):
        super().__init__(S, force_recalc, **kwargs)
        self._energy = np.array([])
        self._wl = np.array([])
        self._k = np.array([])
        self._theta = np.zeros([1, 1])
        self._qz = np.zeros([1, 1])

        self.polarizations = {0: 'unpolarized',
                              1: 'circ +',
                              2: 'circ -',
                              3: 'sigma',
                              4: 'pi'}

        self.pol_in_state = 3  # sigma
        self.pol_out_state = 0  # no-analyzer
        self.pol_in = None
        self.pol_out = None
        self.set_polarization(self.pol_in_state, self.pol_out_state)

    def __str__(self, output=[]):
        """String representation of this class"""
        output = [['energy', self.energy[0] if np.size(self.energy) == 1 else
                   '{:f} .. {:f}'.format(np.min(self.energy), np.max(self.energy))],
                  ['wavelength', self.wl[0] if np.size(self.wl) == 1 else
                   '{:f} .. {:f}'.format(np.min(self.wl), np.max(self.wl))],
                  ['wavenumber', self.k[0] if np.size(self.k) == 1 else
                   '{:f} .. {:f}'.format(np.min(self.k), np.max(self.k))],
                  ['theta', self.theta[0] if np.size(self.theta) == 1 else
                   '{:f} .. {:f}'.format(np.min(self.theta), np.max(self.theta))],
                  ['q_z', self.qz[0] if np.size(self.qz) == 1 else
                   '{:f} .. {:f}'.format(np.min(self.qz), np.max(self.qz))],
                  ['incoming polarization', self.polarizations[self.pol_in_state]],
                  ['analyzer polarization', self.polarizations[self.pol_out_state]],
                  ] + output
        return super().__str__(output)

    def set_polarization(self, pol_in_state, pol_out_state):
        """set_polarization

        Sets the incoming and analyzer (outgoing) polarization

        """
        self.set_incoming_polarization(pol_in_state)
        self.set_outgoing_polarization(pol_out_state)

    def get_hash(self, strain_vectors, **kwargs):
        """get_hash

        Returns a unique hash given by the energy :math:`E`,
        :math:`q_z` range, polarization states and the strain vectors as
        well as the sample structure hash for relevant xray parameters.
        Optionally, part of the strain_map is used.

        """
        param = [self.pol_in_state, self.pol_out_state, self._qz, self._energy, strain_vectors]

        if 'strain_map' in kwargs:
            strain_map = kwargs.get('strain_map')
            if np.size(strain_map) > 1e6:
                strain_map = strain_map.flatten()[0:1000000]
            param.append(strain_map)

        return self.S.get_hash(types='xray') + '_' + make_hash_md5(param)

    def get_polarization_factor(self, theta):
        """get_polarization_factor

        Returns the polarization factor :math:`P(\\vartheta)` for a
        given incident angle :math:`\\vartheta` for the case of
        s-polarization (pol = 0), or p-polarization (pol = 1), or
        unpolarized X-rays (pol = 0.5):

        .. math::

            P(\\vartheta) = \sqrt{(1-\mbox{pol}) + \mbox{pol} \cdot \cos(2\\vartheta)}

        """

        return np.sqrt((1-self.pol_in) + self.pol_in*np.cos(2*theta)**2)

    def update_experiment(self, caller):
        """update experimental parameters

        Recalculate energy, wavelength, and wavevector as well as theta
        and the scattering vector in case any of these has changed.

        .. math::

            \lambda = \\frac {hc} {E}

            E = \\frac {hc} {\lambda}

            k = \\frac {2\pi} {\lambda}

            \\vartheta = \\arcsin{ \\frac{\lambda q_z}{4\pi}}

            q_z = 2k\\sin{\\vartheta}

        """
        from scipy import constants
        if caller != 'energy':
            if caller == 'wl':  # calc energy from wavelength
                self._energy = Q_((constants.h*constants.c)/self._wl, 'J').to('eV').magnitude
            elif caller == 'k':  # calc energy von wavevector
                self._energy = \
                    Q_((constants.h*constants.c)/(2*np.pi/self._k), 'J').to('eV').magnitude
        if caller != 'wl':
            if caller == 'energy':  # calc wavelength from energy
                self._wl = (constants.h*constants.c)/self.energy.to('J').magnitude
            elif caller == 'k':  # calc wavelength from wavevector
                self._wl = 2*np.pi/self._k
        if caller != 'k':
            if caller == 'energy':  # calc wavevector from energy
                self._k = 2*np.pi/self._wl
            elif caller == 'wl':  # calc wavevector from wavelength
                self._k = 2*np.pi/self._wl

        if caller != 'theta':
            self._theta = np.arcsin(np.outer(self._wl, self._qz[0, :])/np.pi/4)
        if caller != 'qz':
            self._qz = np.outer(2*self._k, np.sin(self._theta[0, :]))

    @property
    def energy(self):
        """ndarray[float]: photon energies :math:`E` of scattering light"""
        return Q_(self._energy, u.eV)

    @energy.setter
    def energy(self, energy):
        self._energy = np.array(energy.to('eV').magnitude, ndmin=1)
        self.update_experiment('energy')

    @property
    def wl(self):
        """ndarray[float]: wavelengths :math:`\lambda` of scattering light"""
        return Q_(self._wl, u.m).to('nm')

    @wl.setter
    def wl(self, wl):
        self._wl = np.array(wl.to_base_units().magnitude, ndmin=1)
        self.update_experiment('wl')

    @property
    def k(self):
        """ndarray[float]: wavenumber :math:`k` of scattering light"""
        return Q_(self._k, 1/u.m).to('1/nm')

    @k.setter
    def k(self, k):
        self._k = np.array(k.to_base_units().magnitude, ndmin=1)
        self.update_experiment('k')

    @property
    def theta(self):
        """ndarray[float]: incidence angles :math:`\theta` of scattering light"""
        return Q_(self._theta, u.rad).to('deg')

    @theta.setter
    def theta(self, theta):
        self._theta = np.array(theta.to_base_units().magnitude, ndmin=1)
        if self._theta.ndim < 2:
            self._theta = np.tile(self._theta, (len(self._energy), 1))
        self.update_experiment('theta')

    @property
    def qz(self):
        """ndarray[float]: sscattering vector :math:`q_z` of scattering light"""
        return Q_(self._qz, 1/u.m).to('1/nm')

    @qz.setter
    def qz(self, qz):
        self._qz = np.array(qz.to_base_units().magnitude, ndmin=1)
        if self._qz.ndim < 2:
            self._qz = np.tile(self._qz, (len(self._energy), 1))
        self.update_experiment('qz')
