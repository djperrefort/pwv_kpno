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
#    along with pwv_kpno.  If not, see <http://www.gnu.org/licenses/>.

"""This document defines end user functions for accessing the modeled
atmospheric transmission.  It relies heavily on the atmospheric transmission
models generated by _atm_model.py and the modeled PWV level at Kitt Peak
generated by _serve_pwv_data.py.
"""

from datetime import datetime, timedelta

import numpy as np
from pytz import utc
from astropy.table import Table

from ._settings import settings
from ._serve_pwv_data import _pwv_date, timestamp

__authors__ = ['Daniel Perrefort']
__copyright__ = 'Copyright 2017, Daniel Perrefort'
__credits__ = ['Michael Wood-Vasey']

__license__ = 'GPL V3'
__email__ = 'djperrefort@pitt.edu'
__status__ = 'Development'


def _raise_pwv(pwv):
    """Raise exception if pwv argument has wrong value

    PWV values should be in the range 0 <= pwv <= 30.1

    Args:
        pwv (int, float): A PWV concentration in mm
    """

    if pwv < 0:
        raise ValueError('PWV concentration cannot be negative')


def trans_for_pwv(pwv):
    # type: (float) -> Table
    """Return the atmospheric transmission due a given PWV concentration in mm

    For a given precipitable water vapor concentration, return the modeled
    atmospheric transmission function.

    Args:
        pwv (float): A PWV concentration in mm

    Returns:
        The modeled transmission function as an astropy table
    """

    _raise_pwv(pwv)

    atm_model = Table.read(settings._atm_model_path)
    atm_model['transmission'] = np.exp(- pwv * atm_model['mm_cm_2'])
    atm_model.remove_column('mm_cm_2')
    atm_model['wavelength'].unit = 'angstrom'

    return atm_model


def _raise_transmission_args(date, airmass):
    """Raise exception if arguments have wrong type or value

    Args:
        date    (datetime.datetime): A datetime value
        airmass             (float): An airmass value
    """

    if not isinstance(date, datetime):
        raise TypeError("Argument 'date' (pos 1) must be a datetime instance")

    if date.tzinfo is None:
        err_msg = "Argument 'date' (pos 1) has no timezone information."
        raise ValueError(err_msg)

    if date.year < 2010:
        err_msg = "Cannot model years before 2010 (passed {})"
        raise ValueError(err_msg.format(date.year))

    if date > datetime.now(utc):
        err_msg = "Cannot model dates in the future (passed {})"
        raise ValueError(err_msg.format(date))

    if not isinstance(airmass, (float, int)):
        raise TypeError("Argument 'airmass' (pos 2) must be an int or float")


def _raise_available_data(date, pwv_model):
    """Check if a date falls within the range of data in an astropy table

    Args:
        date   (datetime): A timezone aware datetime
        pwv_model (Table): An astropy table containing column 'date'
    """

    # Check date falls within the range of available PWV data
    time_stamp = timestamp(date)
    w_data_less_than = np.where(pwv_model['date'] < time_stamp)[0]
    if len(w_data_less_than) < 1:
        min_date = datetime.utcfromtimestamp(min(pwv_model['date']))
        msg = 'No local SuomiNet data found for datetimes before {0}'
        raise ValueError(msg.format(min_date))

    w_data_greater_than = np.where(time_stamp < pwv_model['date'])[0]
    if len(w_data_greater_than) < 1:
        max_date = datetime.utcfromtimestamp(max(pwv_model['date']))
        msg = 'No local SuomiNet data found for datetimes after {0}'
        raise ValueError(msg.format(max_date))

    # Check for SuomiNet data available near the given date
    diff = pwv_model['date'] - time_stamp
    interval = min(diff[diff > 0]) - max(diff[diff < 0])
    one_day_in_seconds = 24 * 60 * 60

    if one_day_in_seconds <= interval:
        msg = ('Specified datetime falls within interval of missing SuomiNet' +
               ' data larger than 1 day ({0} interval found).')
        raise ValueError(msg.format(timedelta(seconds=interval)))


def _trans_for_date(date, airmass, test_model=None):
    """Return a model for the atmospheric transmission function due to PWV

    Args:
        date (datetime.datetime): The datetime of the desired model
        airmass          (float): The airmass of the desired model
        test_model       (Table): A mock PWV model used by the test suite

    Returns:
        The modeled transmission function as an astropy table
    """

    pwv = _pwv_date(date, airmass, test_model)
    return trans_for_pwv(pwv)


def trans_for_date(date, airmass):
    # type: (datetime, float) -> Table
    """Return a model for the atmospheric transmission function due to PWV

    For a given datetime and airmass, return a model for the atmospheric
    transmission function due to precipitable water vapor at Kitt Peak National
    Observatory.

    Args:
        date (datetime.datetime): The datetime of the desired model
        airmass          (float): The airmass of the desired model

    Returns:
        The modeled transmission function as an astropy table
    """

    return _trans_for_date(date, airmass, test_model=None)
