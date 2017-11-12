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

"""This file tests that the necessary SuomiNet data files are available within
the package, and that the config file accurately represents what data is
available.
"""

import os
from datetime import datetime

import unittest

from pwv_kpno.end_user_functions import available_data

PACKAGE_DATA_DIR = '../pwv_kpno/suomi_data/'
COFIG_PATH = '../pwv_kpno/CONFIG.txt'


class TestCorrectDataFiles(unittest.TestCase):
    """Test appropriate SuomiNet data files are included with the package"""

    @classmethod
    def setUpClass(self):
        """Determine what data files are currently included in the package"""

        self.data_file_years = set()
        self.data_file_GPS_ids = set()

        for fname in os.listdir(PACKAGE_DATA_DIR):
            if fname.endswith('.plt'):
                self.data_file_years.add(int(fname[7:11]))
                self.data_file_GPS_ids.add(fname[0:4])

    def test_correct_years(self):
        """Test that data files correspond to appropriate years"""

        expected_years = set(range(2010, datetime.now().year))
        missing_years = expected_years - self.data_file_years
        extra_years = self.data_file_years - expected_years

        error_msg = 'Missing SuomiNet data files for years {}'
        self.assertFalse(missing_years, error_msg.format(missing_years))

        error_msg = 'Extra SuomiNet data for years {}'
        self.assertFalse(extra_years, error_msg.format(extra_years))

    def test_correct_gps_ids(self):
        """Test data files correspond to appropriate GPS receivers"""

        expected_ids = {'KITT', 'P014', 'SA46', 'SA48', 'AZAM'}
        missing_ids = expected_ids - self.data_file_GPS_ids
        bad_ids = self.data_file_GPS_ids - expected_ids

        error_msg = 'Missing data files for SuomiNet id {}'
        self.assertFalse(missing_ids, error_msg.format(missing_ids))

        error_msg = 'Unexpected data file with SuomiNet id {}'
        self.assertFalse(bad_ids, error_msg.format(bad_ids))


class TestConfigFile(unittest.TestCase):
    """Test config.txt has the appropriate data"""

    def test_config_matches_data(self):
        """Compare years in config file with years of present data files"""

        config_data = set(available_data())
        expected_years = set(range(2010, datetime.now().year))
        missing_years = expected_years - config_data
        extra_years = config_data - expected_years

        error_msg = 'Missing years in config file ({})'
        self.assertFalse(missing_years, error_msg.format(missing_years))

        error_msg = 'Extra years in config file ({})'
        self.assertFalse(extra_years, error_msg.format(extra_years))
