#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

#    This file is part of the pwv_kpno software package.
#
#    The pwv_kpno package is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The pwv_kpno package is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pwv_kpno. If not, see <http://www.gnu.org/licenses/>.

"""The ConfigBuilder class is provided to create custom config files used in
the pwv_kpno package.
"""

import os
from warnings import warn

import numpy as np

from ._atm_model import create_pwv_atm_model

__authors__ = ['Daniel Perrefort']
__copyright__ = 'Copyright 2017, Daniel Perrefort'

__license__ = 'GPL V3'
__email__ = 'djperrefort@pitt.edu'
__status__ = 'Development'

# List of params that data cuts can be applied for
CUT_PARAMS = ['PWV', 'PWVerr', 'ZenithDelay', 'SrfcPress', 'SrfcTemp', 'SrfcRH']


class ConfigBuilder:
    """This class is used to build custom config files for the pwv_kpno package

    Attributes:
        data_cuts         (dict): Specifies data ranges to ignore
        loc_name           (str): Desired name of the custom location
        primary_rec        (str): SuomiNet ID code for the primary GPS receiver
        sup_recs          (list): List of id codes for supplemental receivers
        wavelengths    (ndarray): Array of wavelengths in Angstroms
        cross_sections (ndarray): Array of MODTRAN cross sections in cm^2

    Methods:
        save : Create a custom config file <loc_name>.ecsv in a given directory
    """

    def __init__(self, **kwargs):
        self.data_cuts = dict()
        self.loc_name = None  # type: str
        self.primary_rec = None  # type: str
        self.sup_rec = []
        self.wavelengths = None  # type: np.ndarray
        self.cross_sections = None  # type: np.ndarray

        for key, value in kwargs.items():
            setattr(self, key, value)

    def _raise_unset_attributes(self):
        """Ensure user has assigned values to required attributes"""

        err_msg = 'Must specify attribute {} before saving.'
        attrs = ['loc_name', 'primary_rec', 'wavelengths', 'cross_sections']
        for value in attrs:
            if getattr(self, value) is None:
                raise ValueError(err_msg.format(value))

    def _warn_data_cuts(self):
        """Raise warnings if data cuts are not the correct format

        Data cuts should be of the form:
            {cut param: [[lower bound, upper bound], ...], ...}
        """

        for key, value in self.data_cuts:
            if key not in CUT_PARAMS:
                warn(
                    'Cut parameter {} does not correspond to any parameter '
                    'used by pwv_kpno'.format(key)
                )

            value = np.array(value)
            if not len(value.shape) == 2:
                warn(
                    'Cut boundaries for parameter {} '
                    'is not a two dimensional array'.format(key)
                )

    def _warn_loc_name(self):
        """Raise warnings if loc_name is not the correct format

        Location names should be lowercase strings.
        """

        if not self.loc_name.isupper():
            warn(
                'SuomiNet uses lowercase location names. Location name {} will'
                ' be saved as {}.'.format(self.loc_name, self.loc_name.upper())
            )

    def _warn_id_codes(self):
        """Raise warnings if SuomiNet ID codes are not the correct format

        SuomiNet ID codes should be four characters long and uppercase.
        """

        all_id_codes = self.sup_rec.copy()
        all_id_codes.append(self.primary_rec)
        for id_code in all_id_codes:
            if len(id_code) != 4:
                warn(
                    'ID is not of expected length 4: {}'.format(id_code)
                )

            if not id_code.isupper():
                warn(
                    'SuomiNet ID codes should be uppercase. ID code {} will'
                    ' be saved as {}.'.format(id_code, id_code.isupper())
                )

    def _create_config_dict(self):
        """Create a dictionary with config data for this location

        Returns:
            A dictionary storing location settings
        """

        config_data = dict()
        self._warn_data_cuts()
        config_data['data_cuts'] = self.data_cuts

        self._warn_loc_name()
        config_data['loc_name'] = self.loc_name.lower()

        self._warn_id_codes()
        config_data['primary_rec'] = self.primary_rec.upper()
        config_data['sup_rec'] = [id_code.upper() for id_code in self.sup_rec]
        return config_data

    def save(self, out_dir):
        # type: (str) -> None
        """Create a custom config file <out_dir>/<self.loc_name>.ecsv

        Args:
            out_dir (str): The desired output directory
        """

        self._raise_unset_attributes()
        model = create_pwv_atm_model(mod_lambda=np.array(self.wavelengths),
                                     mod_cs=np.array(self.cross_sections),
                                     out_lambda=np.array(self.wavelengths))

        model.meta = self._create_config_dict()
        out_path = os.path.join(out_dir, self.loc_name + '.ecsv')
        model.write(out_path)

    def __repr__(self):
        rep = '<ConfigBuilder loc_name={}, primary_rec={}>'
        return rep.format(self.loc_name, self.primary_rec)
