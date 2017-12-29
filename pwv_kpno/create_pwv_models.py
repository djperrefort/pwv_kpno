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

"""This code downloads precipitable water vapor (PWV) measurements from
from suominet.ucar.edu for Kitt Peak and other nearby locations. Using
these values, first order polynomials are fitted to relate the PWV
level at nearby locations to the PWV level at Kitt Peak. The resulting
polynomials are then used to supplement the PWV measurements taken at
Kitt Peak for times when no Kitt Peak data is available.

Data downloaded from SuomiNet is added to a master table located at
PWV_TAB_DIR/measured.csv. Supplemented PWV values are stored in a master table
located at PWV_TAB_DIR/modeled.csv. All datetimes are recorded as timestamps
and PWV measurements are represented in units of millimeters.

For more details on the SuomiNet project see
http://www.suominet.ucar.edu/overview.html.
"""

from collections import Counter
from datetime import datetime, timedelta
import os
from warnings import warn

import requests
import numpy as np
from astropy.table import Table, join, vstack, unique

from .settings import Settings

__authors__ = 'Daniel Perrefort'
__copyright__ = 'Copyright 2016, Daniel Perrefort'
__credits__ = 'Jessica Kroboth'

__license__ = 'GPL V3'
__email__ = 'djperrefort@gmail.com'
__status__ = 'Development'

# Necessary directory paths
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(FILE_DIR, 'locations/kitt_peak')  # package data tables
SUOMI_DIR = os.path.join(FILE_DIR, 'suomi_data')          # SuomiNet data files


def _suomi_date_to_timestamp(year, days_str):
    """Return seconds since epoch of a datetime provided in DDD.YYYYY format

    Convert the datetime notation used by SuomiNet to a UTC timestamp. The
    SuomiNet format consists of the day of the year (1 to 365) followed by the
    decimal number of hours that have passed in the given day. For example,
    February 1st, 00:15 would be 36.01042.

    Args:
        year     (int): The year of the desired timestamp
        days_str (str): The number of days that have passed since january 1st

    Returns:
        The seconds from UTC epoch to the provided date as a float
    """

    jan_1st = datetime(year=year, month=1, day=1)
    date = jan_1st + timedelta(days=float(days_str) - 1)

    # Correct for round off error in SuomiNet date format
    date = date.replace(second=0, microsecond=0)
    if date.minute % 5:
        date += timedelta(minutes=1)

    timestamp = (date - datetime(1970, 1, 1)).total_seconds()
    return timestamp


def _read_file(path):
    """Return PWV measurements from a SuomiNet data file as an astropy table

    Expects data files from http://www.suominet.ucar.edu/data.html under the
    "Specific station - All year hourly" section. The returned astropy table
    has one column with datetimes named 'date', and one with PWV measurements
    named using the id code for the relevant GPS receiver. Datetimes are
    expressed as UNIX timestamps and PWV is measured in millimeters.

    Data is removed from the array for dates where the PWV level is negative.
    This condition is equivalent to checking for dates when a GPS receiver is
    offline. Data is also removed for dates with multiple, unequal entries.
    Note that this may result in an empty table being returned. Credit goes to
    Jessica Kroboth for identifying these conditions.

    Args:
        path (str): File path to be read

    Returns:
        An astropy Table with data from path
    """

    # Read data from file
    data = np.genfromtxt(path, usecols=[0, 1],
                         names=['date', 'pwv'],
                         dtype=[(np.str_, 16), float])

    data = data[data['pwv'] > 0]  # Remove data with PWV < 0
    data = np.unique(data)  # Sometimes SuomiNet records duplicate entries

    # Remove any remaining entries with duplicate dates but different data
    dup_dates = (Counter(data['date']) - Counter(set(data['date']))).keys()
    ind = [(x not in dup_dates) for x in data['date']]
    out_table = Table(np.extract(ind, data), names=['date', path[-15:-11]])

    # Convert dates to UNIX timestamp
    if out_table:
        year = int(path[-8:-4])
        to_timestamp_vectorized = np.vectorize(_suomi_date_to_timestamp)
        out_table['date'] = to_timestamp_vectorized(year, out_table['date'])

    # Remove data from faulty receiver at Kitt Peak (Jan 2016 through Mar 2016)
    if path.endswith('KITThr_2016.plt') or path.endswith('KITTdy_2016.plt'):
        april_2016_begins = 1459468800.0
        out_table = out_table[april_2016_begins < out_table['date']]

    return out_table


def _download_suomi_files(year, site_id):
    """Download SuomiNet data for a given year and SuomiNet id

    For a given year and SuomiNet id, download data from the corresponding GPS
    receiver. Files are downloaded from both the daily and hourly data
    releases. Any existing data files are overwritten.

    Args:
        year    (int): A year to download data for
        site_id (str): A SuomiNet receiver id code (eg. KITT)

    Returns:
        A list of file paths containing downloaded data
    """

    downloaded_paths = []
    day_path = os.path.join(SUOMI_DIR, '{0}dy_{1}.plt')
    day_url = 'http://www.suominet.ucar.edu/data/staYrDay/{0}pp_{1}.plt'
    hour_path = os.path.join(SUOMI_DIR, '{0}hr_{1}.plt')
    hour_url = 'http://www.suominet.ucar.edu/data/staYrHr/{0}nrt_{1}.plt'

    if not os.path.exists(SUOMI_DIR):
        os.mkdir(SUOMI_DIR)

    for general_path, url in ((day_path, day_url), (hour_path, hour_url)):
        response = requests.get(url.format(site_id, year))

        try:
            response.raise_for_status()
            path = general_path.format(site_id, year)
            with open(path, 'wb') as ofile:
                ofile.write(response.content)

            downloaded_paths.append(path)

        except requests.exceptions.HTTPError:
            if response.status_code != 404:
                raise

    return downloaded_paths


def _download_suomi_data_for_year(yr):
    """Download and return data from all five SuomiNet sites for a given year

    Downloaded data for the SuomiNet sites KITT, SA48, SA46, P014, and AZAM.
    Return this data as an astropy table with all available data from the daily
    data releases supplemented by the hourly release data.

    Args:
        yr (int): The year of the desired data

    Returns:
        An astropy Table of the combined downloaded data for the given year.
    """

    combined_data = None
    for site_id in Settings().current_location.enabled_receivers:
        site_data = None
        for path in _download_suomi_files(yr, site_id):
            new_data = _read_file(path)
            if not site_data and new_data:
                site_data = new_data

            elif new_data:
                site_data = unique(vstack([site_data, new_data]),
                                   keys=['date'])

        if not combined_data and site_data:
            combined_data = site_data

        elif site_data:
            combined_data = join(combined_data, site_data,
                                 join_type='outer', keys=['date'])

    if not combined_data:
        msg = 'No SuomiNet data downloaded for year {}'.format(yr)
        warn(msg, RuntimeWarning)

    return combined_data


def update_suomi_data(year=None):
    """Download data from SuomiNet and update PWV_TAB_DIR/measured_pwv.csv

    If a year is provided, download SuomiNet data for that year to SUOMI_DIR.
    If not, download all available data not included with the release of this
    package version. Use this data to update the master table of PWV
    measurements located at PWV_TAB_DIR/measured_pwv.csv.

    Args:
        year (int): The year to update data for

    Returns:
        A list of years for which data was updated
    """

    # Get any local data that has already been downloaded
    local_data_path = os.path.join(DATA_DIR, 'measured_pwv.csv')
    local_data = Table.read(local_data_path)

    current_location = Settings().current_location
    current_years = set(current_location.available_years)
    if year is None:
        # Todo: Add test for this code block
        all_years = set(range(2010, datetime.now().year + 1))
        years = all_years - current_years
        years.add(max(current_years))

    else:
        years = {year}

    # Download data from SuomiNet
    for yr in years:
        new_data = _download_suomi_data_for_year(yr)
        local_data = unique(vstack([local_data, new_data]),
                            keys=['date'],
                            keep='last')

        current_years.add(yr)

    # Update local files
    local_data.write(local_data_path, overwrite=True)

    # Todo: Reduce the use of type casting between lists and sets
    current_location._replace_years(list(current_years))

    return current_years


def update_pwv_model():
    """Create a new model for the PWV level at Kitt Peak

    Create first order polynomials relating the PWV measured by GPS receivers
    near Kitt Peak to the PWV measured at Kitt Peak (one per off site receiver)
    Use these polynomials to supplement PWV measurements taken at Kitt Peak for
    times when no Kitt Peak data is available. Write the supplemented PWV
    data to a csv file at PWV_TAB_DIR/measured.csv.
    """

    # Credit belongs to Jessica Kroboth for suggesting the use of a linear fit
    # to supplement PWV measurements when no Kitt Peak data is available.

    # Read the local PWV data from file
    pwv_data = Table.read(os.path.join(DATA_DIR, 'measured_pwv.csv'))
    gps_receivers = set(pwv_data.colnames) - {'date', 'KITT'}

    # Generate the fit parameters
    for receiver in gps_receivers:
        # Identify rows with data for both KITT and receiver
        kitt_index = np.logical_not(pwv_data['KITT'].mask)
        rec_index = np.logical_not(pwv_data[receiver].mask)
        matching_indices = np.where(np.logical_and(kitt_index, rec_index))[0]

        # Generate and apply a first order fit
        fit_data = pwv_data['KITT', receiver][list(matching_indices)]
        fit = np.polyfit(fit_data[receiver], fit_data['KITT'], 1)
        pwv_data[receiver] = np.poly1d(fit)(pwv_data[receiver])

    # Average together the modeled PWV values from all receivers except KITT
    cols = [c for c in pwv_data.itercols() if c.name not in ['date', 'KITT']]
    avg_pwv = np.ma.average(cols, axis=0)

    # Supplement KITT data with averaged fits
    sup_data = np.ma.where(pwv_data['KITT'].mask, avg_pwv, pwv_data['KITT'])

    # Write results to file
    out = Table([pwv_data['date'], sup_data], names=['date', 'pwv'])
    out = out[np.where(out['pwv'] > 0)[0]]
    out.write(os.path.join(DATA_DIR, 'modeled_pwv.csv'), overwrite=True)
