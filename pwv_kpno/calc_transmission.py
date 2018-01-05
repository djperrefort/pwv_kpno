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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pwv_kpno.  If not, see <http://www.gnu.org/licenses/>.

"""This document defines end user functions for accessing the modeled
atmospheric transmission.  It relies heavily on the atmospheric transmission
models generated by create_atm_models.py and the modeled PWV level at Kitt Peak
generated by create_pwv_models.py. End user functions defined in this document
include `transmission` and `transmission_pwv`.
"""

import os
from datetime import datetime, timedelta

import numpy as np
from pytz import utc
from astropy.table import Table
from scipy.interpolate import interpn

from pwv_kpno.settings import Settings

__author__ = 'Daniel Perrefort'
__copyright__ = 'Copyright 2017, Daniel Perrefort'
__credits__ = ['Michael Wood-Vasey']

__license__ = 'GPL V3'
__email__ = 'djperrefort@gmail.com'
__status__ = 'Development'

# Paths of data file for Kitt Peak
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
ATM_MODEL_PATH = os.path.join(FILE_DIR, 'locations/{}/atm_model.csv')
PWV_MODEL_PATH = os.path.join(FILE_DIR, 'locations/{}/modeled_pwv.csv')


def _timestamp(date):
    """Returns seconds since epoch of a UTC datetime in %Y-%m-%dT%H:%M format

    This function provides comparability for Python 2.7, for which the
    datetime.timestamp method was not yet available.

    Args:
        date (datetime.datetime): A datetime to find the timestamp for

    Returns:
        The timestamp of the provided datetime as a float
    """

    unix_epoch = datetime(1970, 1, 1, tzinfo=utc)
    utc_date = date.astimezone(utc)
    timestamp = (utc_date - unix_epoch).total_seconds()
    return timestamp


def _check_transmission_args(date, airmass, model):
    """Check arguments for the function `transmission`

    This function provides argument checks for the `transmission` function. It
    checks argument types, if a datetime falls within the range of the locally
    available SuomiNet data, and if SuomiNet data is available near that
    datetime.

    Args:
        date    (datetime.datetime): A datetime value
        airmass             (float): An airmass value
        model (astropy.table.Table): A model for the PWV level at KPNO

    Returns:
        None
    """

    # Check argument types
    if not isinstance(date, datetime):
        raise TypeError("Argument 'date' (pos 1) must be a datetime instance")

    if date.tzinfo is None:
        msg = "Argument 'date' (pos 1) has no timezone information."
        raise ValueError(msg)

    if not isinstance(airmass, (float, int)):
        raise TypeError("Argument 'airmass' (pos 2) must be an int or float")

    # Check date falls within the range of available PWV data
    timestamp = _timestamp(date)
    w_data_less_than = np.where(model['date'] < timestamp)[0]
    if len(w_data_less_than) < 1:
        min_date = datetime.utcfromtimestamp(min(model['date']))
        msg = 'No local SuomiNet data found for datetimes before {0}'
        raise ValueError(msg.format(min_date))

    w_data_greater_than = np.where(timestamp < model['date'])[0]
    if len(w_data_greater_than) < 1:
        max_date = datetime.utcfromtimestamp(max(model['date']))
        msg = 'No local SuomiNet data found for datetimes after {0}'
        raise ValueError(msg.format(max_date))

    # Check for SuomiNet data available near the given date
    diff = model['date'] - timestamp
    interval = min(diff[diff > 0]) - max(diff[diff < 0])
    three_days_in_seconds = 3 * 24 * 60 * 60

    if three_days_in_seconds < interval:
        msg = ('Specified datetime falls within interval of missing SuomiNet' +
               ' data larger than 3 days ({0} interval found).')
        raise ValueError(msg.format(timedelta(seconds=interval)))


def transmission_pwv(pwv):
    """Return the atmospheric transmission due a given PWV concentration in mm

    For a given precipitable water vapor concentration, return the modeled
    atmospheric transmission function. The modeled transmission is returned as
    an astropy table with the columns 'wavelength' and 'transmission'.
    Wavelength values range from 7000 to 10,000 angstroms.

    Args:
        pwv (float): The PWV concentration of the desired transmission in mm

    Returns:
        The modeled transmission function as an astropy table.
    """

    if pwv < 0:
        raise ValueError('PWV concentration cannot be negative')

    if pwv > 30.1:
        err_msg = 'Cannot provide models for PWV concentrations above 30.1'
        raise ValueError(err_msg)

    location_name = Settings().current_location.name
    atm_model = Table.read(ATM_MODEL_PATH.format(location_name))
    wavelengths = atm_model['wavelength']
    atm_model.remove_column('wavelength')

    pwv_values = []
    array_shape = (len(atm_model.colnames), len(wavelengths))
    transmission_models = np.zeros(array_shape, dtype=np.float)

    for i, column in enumerate(atm_model.itercols()):
        pwv_values.append(float(column.name))
        transmission_models[i, :] = column

    interp_trans = interpn(points=(pwv_values, wavelengths),
                           values=transmission_models,
                           xi=np.array([[pwv, x] for x in wavelengths]))

    trans_func = Table([wavelengths, interp_trans],
                       names=['wavelength', 'transmission'],
                       dtype=[float, float])

    trans_func['wavelength'].unit = 'angstrom'
    trans_func['transmission'].unit = 'percent'
    return trans_func


def transmission(date, airmass, test_model=None):
    """Return a model for the atmospheric transmission function due to PWV

    For a given datetime and airmass, return a model for the atmospheric
    transmission function due to precipitable water vapor (PWV) at Kitt Peak.
    The modeled transmission is returned as an astropy table with the columns
    'wavelength' and 'transmission'. Wavelength values range from 7000 to
    10,000 angstroms.

    Args:
        date (datetime.datetime): The datetime of the desired model
        airmass          (float): The airmass of the desired model

    Returns:
        The modeled transmission function as an astropy table
    """

    # Check for valid arguments
    if test_model is None:
        location_name = Settings().current_location.name
        pwv_model = Table.read(PWV_MODEL_PATH.format(location_name))

    else:
        pwv_model = test_model

    _check_transmission_args(date, airmass, pwv_model)

    # Determine the PWV level along line of sight as pwv(zenith) * airmass
    timestamp = _timestamp(date)
    pwv = np.interp(timestamp, pwv_model['date'], pwv_model['pwv']) * airmass
    return transmission_pwv(pwv)
