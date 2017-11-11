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
#    along with pwv_kpno. If not, see <http://www.gnu.org/licenses/>.

"""This file tests that SuomiNet data is downloaded and parsed correctly. The
tests below contribute to coverage of create_pwv_models.py
"""

import os
from datetime import datetime

import unittest
from pytz import utc

from pwv_kpno.create_pwv_models import _download_suomi_data_for_year
from pwv_kpno.create_pwv_models import _read_file
from pwv_kpno.create_pwv_models import _str_to_timestamp

SPATH = '../pwv_kpno/suomi_data/'  # Package directory of SuomiNet data files


def timestamp(date):
    """Returns seconds since UTC epoch of a datetime

    This function provides compatibility for Python 2.7, for which the
    datetime.timestamp method was not yet available.

    Args:
        date (datetime): A datetime to convert to timestamp

    Returns:
        The timestamp of the provided datetime as a float
    """

    unix_epoch = datetime(1970, 1, 1, tzinfo=utc)
    utc_date = date.astimezone(utc)
    total_seconds = (utc_date - unix_epoch).total_seconds()
    return total_seconds


class TestDateFormatConversion(unittest.TestCase):
    """Tests for create_pwv_models._str_to_timestamp"""

    def test_roundoff_error(self):
        """Test returned timestamps for round off error"""

        # Dates with known round off error before bug fix in 0.9.13
        jan_01_2010_01_15 = datetime(2010, 1, 1, 1, 15, tzinfo=utc)
        jan_01_2010_02_45 = datetime(2010, 1, 1, 2, 45, tzinfo=utc)
        jan_01_2010_04_15 = datetime(2010, 1, 1, 4, 15, tzinfo=utc)

        error_msg = 'Incorrect timestamp for {}'
        self.assertEqual(_str_to_timestamp(2010, '1.05208'),
                         timestamp(jan_01_2010_01_15),
                         error_msg.format(jan_01_2010_01_15))

        self.assertEqual(_str_to_timestamp(2010, '1.11458'),
                         timestamp(jan_01_2010_02_45),
                         error_msg.format(jan_01_2010_02_45))

        self.assertEqual(_str_to_timestamp(2010, '1.17708'),
                         timestamp(jan_01_2010_04_15),
                         error_msg.format(jan_01_2010_04_15))

    def test_dates_out_of_data_range(self):
        """Test timestamp calculation for dates outside SuomiNet data range"""

        jan_01_2000_00_15 = datetime(2000, 1, 1, 0, 15, tzinfo=utc)
        dec_31_2021_23_15 = datetime(2021, 12, 31, 23, 15, tzinfo=utc)

        error_msg = 'Incorrect timestamp for {}'
        self.assertEqual(_str_to_timestamp(2000, '1.01042'),
                         timestamp(jan_01_2000_00_15),
                         error_msg.format(jan_01_2000_00_15))

        self.assertEqual(_str_to_timestamp(2021, '365.96875'),
                         timestamp(dec_31_2021_23_15),
                         error_msg.format(dec_31_2021_23_15))


class TestSuomiNetFileParsing(unittest.TestCase):
    """Tests for create_pwv_models._read_file"""

    def setUp(self):
        """Read in SuomiNet data from data files included with the package"""

        self.kitt_hr_path = 'KITThr_2016.plt'
        self.hitt_dy_path = 'KITTdy_2016.plt'
        self.azam_hr_path = 'AZAMhr_2015.plt'
        self.p014_dy_path = 'P014dy_2012.plt'

        self.kitt_hr_data = _read_file(os.path.join(SPATH, self.kitt_hr_path))
        self.kitt_dy_data = _read_file(os.path.join(SPATH, self.hitt_dy_path))
        self.azam_hr_data = _read_file(os.path.join(SPATH, self.azam_hr_path))
        self.p014_hr_data = _read_file(os.path.join(SPATH, self.p014_dy_path))

    def test_column_names(self):
        """Test returned data has correct columns"""

        k_cols = self.kitt_hr_data.colnames
        a_cols = self.azam_hr_data.colnames
        p_cols = self.p014_hr_data.colnames

        msg = 'Wrong column names returned for {}: ({}).'
        self.assertEqual(k_cols, ['date', 'KITT'], msg.format('KITT', k_cols))
        self.assertEqual(a_cols, ['date', 'AZAM'], msg.format('AZAM', a_cols))
        self.assertEqual(p_cols, ['date', 'P014'], msg.format('P014', p_cols))

    def test_dates_are_unique(self):
        """Test for the removal of any duplicate dates"""

        table_entries = len(self.azam_hr_data)
        unique_dates = len(set(self.azam_hr_data['date']))

        msg = 'Duplicate dates not filtered out when parsing AZAMhr_2015.plt'
        self.assertEqual(table_entries, unique_dates, msg)

    def test_removed_negative_values(self):
        """Test for the removal of any negative PWV values"""

        msg = 'Negative PWV values were returned when parsing {}'
        is_negative_kitt_data = any(self.kitt_hr_data['KITT'] < 0)
        is_negative_azam_data = any(self.azam_hr_data['AZAM'] < 0)
        is_negative_p014_data = any(self.p014_hr_data['P014'] < 0)

        self.assertFalse(is_negative_kitt_data, msg.format(self.kitt_hr_path))
        self.assertFalse(is_negative_azam_data, msg.format(self.azam_hr_path))
        self.assertFalse(is_negative_p014_data, msg.format(self.p014_dy_path))

    def test_removed_bad_kitt_data(self):
        """Test for the removal of Kitt Peak data from jan through mar 2016"""

        april_2016 = timestamp(datetime(2016, 4, 1, tzinfo=utc))
        bad_hr_data = self.kitt_hr_data[self.kitt_hr_data['date'] < april_2016]
        bad_dy_data = self.kitt_dy_data[self.kitt_dy_data['date'] < april_2016]

        self.assertFalse(len(bad_hr_data))
        self.assertFalse(len(bad_dy_data))


class TestSuomiNetDataDownload(unittest.TestCase):
    """Tests for create_pwv_models._download_suomi_data_for_year"""

    def setUp(self):
        """Download data from SuomiNet for 2012 and 2015"""

        self.data_2012 = _download_suomi_data_for_year(2012)
        self.data_2015 = _download_suomi_data_for_year(2015)

    def test_column_names(self):
        """Test downloaded data for correct columns"""

        bad_column_msg = 'Wrong columns for year={}'
        expected_2012_cols = {'date', 'AZAM', 'P014', 'SA46', 'SA48'}
        expected_2015_cols = {'date', 'KITT', 'P014', 'SA46', 'SA48', 'AZAM'}

        retrieved_2012_cols = set(self.data_2012.colnames)
        self.assertEqual(retrieved_2012_cols, expected_2012_cols,
                         bad_column_msg.format(2012))

        retrieved_2015_cols = set(self.data_2015.colnames)
        self.assertEqual(retrieved_2015_cols, expected_2015_cols,
                         bad_column_msg.format(2015))
