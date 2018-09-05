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


"""This code provides access to package wide settings for the pwv_kpno package

For full documentation on a function use the builtin Python `help` function
or see https://mwvgroup.github.io/pwv_kpno/.

An Incomplete Guide to Getting Started:

    # Todo
"""

import json
import os
import shutil
from datetime import datetime
from warnings import warn

import numpy as np
from astropy.table import Table

from ._atm_model import create_pwv_atm_model

__authors__ = ['Daniel Perrefort']
__copyright__ = 'Copyright 2017, Daniel Perrefort'

__license__ = 'GPL V3'
__email__ = 'djperrefort@pitt.edu'
__status__ = 'Release'

# Sites included with release that cannot be overwritten by the user
PROTECTED_NAMES = ['kitt_peak']

# List of params that data cuts can be applied for
CUT_PARAMS = ('PWV', 'PWVerr', 'ZenithDelay', 'SrfcPress', 'SrfcTemp', 'SrfcRH')


class ModelingConfigError(Exception):
    pass


def site_property(f):
    @property
    def wrapper(self, *args, **kwargs):
        if self._site_name is None:
            err_msg = 'No site has been specified for pwv_kpno model.'
            raise ModelingConfigError(err_msg)

        return f(self, *args, **kwargs)

    return wrapper


# Todo: Add usage demo
# Todo: Needs getters and setters
class Settings:
    """Represents pwv_kpno settings for a particular geographical site

    Represents settings for Kitt Peak by default

    Attributes:
        site_name       : The current site being modeled
        available_sites : A list of built in sites that pwv_kpno can model
        receivers       : A list of SuomiNet receivers used by this site
        primary_rec     : The SuomiNet id code for the primary GPS receiver
        supplement_rec  : Same as receivers but without the primary receiver

    Methods:
        set_site      : Configure pwv_kpno to model a given site
        export_config : Save the current site's configuration data to file
    """

    _site_name = None  # The name of the current site
    _config_data = None  # Data from the site's config file

    def __init__(self):
        _file_dir = os.path.dirname(os.path.realpath(__file__))
        self._suomi_dir = os.path.join(_file_dir, 'suomi_data')
        self._loc_dir_unf = os.path.join(_file_dir, 'site_data/{}')
        self._config_path_unf = os.path.join(self._loc_dir_unf, 'config.json')

        atm_dir = os.path.join(_file_dir, 'default_atmosphere/')
        self._h2o_cs_path = os.path.join(atm_dir, 'h2ocs.txt')
        # self._o2_cs_path = os.path.join(atm_dir, 'o2cs.txt')
        # self._o3_cs_path = os.path.join(atm_dir, 'o3cs.txt')

    @property
    def site_name(self):
        # type: () -> str
        return self._site_name

    @site_property
    def primary_rec(self):
        # type: () -> str
        return self._config_data['primary_rec']

    @site_property
    def _loc_dir(self):
        return self._loc_dir_unf.format(self.site_name)

    @property
    def _atm_model_path(self):
        return os.path.join(self._loc_dir, 'atm_model.csv')

    @site_property
    def _config_path(self):
        return self._config_path_unf.format(self.site_name)

    @property
    def _pwv_model_path(self):
        return os.path.join(self._loc_dir, 'modeled_pwv.csv')

    @property
    def _pwv_measred_path(self):
        return os.path.join(self._loc_dir, 'measured_pwv.csv')

    @property
    def available_sites(self):
        # type: () -> list[str]
        """A list of sites for which pwv_kpno has stored settings"""

        return next(os.walk(self._loc_dir_unf.format('')))[1]

    def set_site(self, loc):
        # type: (str) -> None
        """Configure pwv_kpno to model the default_atmosphere at a given site

        See the available_sites attribute for a list of available site names

        Args:
            loc (str): The name of a site to model
        """

        if loc in self.available_sites:
            config_path = self._config_path_unf.format(loc)

        else:
            err_msg = 'No stored settings for site {}'
            raise ValueError(err_msg.format(loc))

        with open(config_path, 'r') as ofile:
            self._config_data = json.load(ofile)

        self._site_name = self._config_data['site_name']

    @site_property
    def _available_years(self):
        """A list of years for which SuomiNet data has been downloaded"""

        with open(self._config_path, 'r') as ofile:
            return sorted(json.load(ofile)['years'])

    def _replace_years(self, yr_list):
        # Replaces the list of years in the site's config file

        # Note: self._config_path calls @site_property decorator
        with open(self._config_path, 'r+') as ofile:
            current_data = json.load(ofile)
            current_data['years'] = list(set(yr_list))
            ofile.seek(0)
            json.dump(current_data, ofile, indent=4, sort_keys=True)
            ofile.truncate()

    @site_property
    def receivers(self):
        # type: () -> list[str]
        """A list of all GPS receivers associated with the current site"""

        # list used instead of .copy for python 2.7 compatibility
        rec_list = list(self._config_data['sup_rec'])
        rec_list.append(self._config_data['primary_rec'])
        return sorted(rec_list)

    @site_property
    def supplement_rec(self):
        # type () -> list[str]
        """A list of all supplementary GPS receivers for the current site"""

        return sorted(self._config_data['sup_rec'])

    @site_property
    def data_cuts(self):
        # type () -> dict
        """Returns restrictions on what SuomiNet measurements to include"""

        return self._config_data['data_cuts']

    def export_config(self, out_dir):
        # type: (str) -> None
        """Save the current site's config file to <out_dir>/<site_name>.ecsv

        Args:
            out_dir (str): The desired output directory
        """

        os.mkdir(out_dir)
        atm_model = Table.read(self._atm_model_path)
        atm_model.meta = self._config_data

        out_path = os.path.join(out_dir, self.site_name + '.ecsv')
        atm_model.write(out_path)

    def import_site(self, path, force_name=None, overwrite=False):
        # type: (str, bool) -> None
        """Load a custom configuration file and save it to the package

        Existing sites are only overwritten if overwrite is set to True.
        The imported site can be assigned an alternative name using the
        forced_name argument.

        Args:
            path       (str): The path of the desired config file
            force_name (str): Optional site name to overwrite config file
            overwrite (bool): Whether to overwrite an existing site
        """

        config_data = Table.read(path)
        if force_name:
            config_data.meta['site_name'] = str(force_name)

        loc_name = config_data.meta['site_name']
        if loc_name in PROTECTED_NAMES:
            err_msg = 'Cannot overwrite protected site name {}'
            raise ValueError(err_msg.format(loc_name))

        out_dir = self._loc_dir_unf.format(loc_name)
        if os.path.exists(out_dir) and not overwrite:
            err_msg = 'Site already exists {}'
            raise ValueError(err_msg.format(loc_name))

        temp_dir = out_dir + '_temp'
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        os.mkdir(temp_dir)
        config_path = os.path.join(temp_dir, 'config.json')
        with open(config_path, 'w') as ofile:
            config_data.meta['years'] = []
            json.dump(config_data.meta, ofile, indent=4, sort_keys=True)

        atm_model_path = os.path.join(temp_dir, 'atm_model.json')
        config_data.write(atm_model_path, format='ascii.csv')

        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)

        shutil.move(temp_dir, out_dir)

    def __repr__(self):
        rep = '<pwv_kpno.Settings, Current Site Name: {}>'
        return rep.format(self.site_name)

    def __str__(self):
        """Print metadata for the current site being modeled"""

        status_table = (
            "                     pwv_kpno Current Site Information\n"
            "============================================================================\n"
            "Site Name:            {} \n"
            "Primary Receiver:     {}\n"
            "Secondary Receivers:\n"
            "    {}\n\n"
            "Available Data:\n"
            "    {}\n\n"
            "                                 Data Cuts\n"
            "============================================================================\n"
            "Reveiver    Value       Type          Lower_Bound          Upper_Bound  unit\n"
            "----------------------------------------------------------------------------"
        )

        if self.supplement_rec:
            receivers = '\n    '.join(self.supplement_rec)

        else:
            receivers = '    NONE'

        if self._available_years:
            years = '\n    '.join(str(x) for x in self._available_years)

        else:
            years = '    NONE'

        status = status_table.format(
            self.site_name,
            self.primary_rec,
            receivers,
            years
        )

        units = {
            'date': 'UTC',
            'PWV': 'mm',
            'PWVerr': 'mm',
            'ZenithDelay': 'mm',
            'SrfcPress': 'mbar',
            'SrfcTemp': 'C',
            'SrfcRH': '%'
        }

        # Todo: This will be simplified once the config file format
        #  is modified in version 1.0.0
        for site, cuts in self.data_cuts.items():
            for value, bounds in cuts.items():
                for start, end in bounds:
                    if value == 'date':
                        cut_type = 'exclusive'
                        start = datetime.utcfromtimestamp(start)
                        end = datetime.utcfromtimestamp(end)

                    else:
                        cut_type = 'inclusive'

                    status += (
                            '\n' +
                            site +
                            value.rjust(13) +
                            cut_type.rjust(11) +
                            str(start).rjust(21) +
                            str(end).rjust(21) +
                            units[value].rjust(6)
                    )

        return status


# This instance should be used package wide to access site settings
settings = Settings()


# Todo: Add test coverage
# Todo: Add usage demo
class ConfigBuilder:
    """The ConfigBuilder class is used to build config files for a custom site

    Default wavelengths and cross sections are provided by MODTRAN estimates
    and range from 3,000 to 12,000 Angstroms in 0.05 Angstrom increments.

    Attributes:
        data_cuts         (dict): Specifies cuts for SuomiNet data
        site_name          (str): Desired name of the custom site
        primary_rec        (str): SuomiNet ID code for the primary GPS receiver
        sup_recs          (list): List of id codes for supplemental receivers
        wavelengths    (ndarray): Array of wavelengths in Angstroms (optional)
        cross_sections (ndarray): Array of PWV cross sections in cm^2 (optional)

    Methods:
        save_to_dir : Create a custom config file <site_name>.ecsv
    """

    def __init__(self, **kwargs):
        self.data_cuts = dict()
        self.site_name = None  # type: str
        self.primary_rec = None  # type: str
        self.sup_rec = []

        settings_obj = Settings()
        settings_obj.set_site('kitt_peak')
        atm_cross_sections = np.genfromtxt(settings_obj._h2o_cs_path).transpose()
        self.wavelengths = atm_cross_sections[0]
        self.cross_sections = atm_cross_sections[1]

        for key, value in kwargs.items():
            setattr(self, key, value)

    def _raise_unset_attributes(self):
        """Ensure user has assigned values to required attributes"""

        err_msg = 'Must specify attribute {} before saving.'
        attrs = ['site_name', 'primary_rec', 'wavelengths', 'cross_sections']
        for value in attrs:
            if getattr(self, value) is None:
                raise ValueError(err_msg.format(value))

    def _warn_data_cuts(self):
        """Raise warnings if data cuts are not the correct format

        Data cuts should be of the form:
            {cut param: [[lower bound, upper bound], ...], ...}
        """

        for dictionary in self.data_cuts.values():
            for key, value in dictionary.items():
                if key not in CUT_PARAMS:
                    warn(
                        'Provided data cut parameter {} does not correspond'
                        ' to any parameter used by pwv_kpno'.format(key)
                    )

                value = np.array(value)
                if not len(value.shape) == 2:
                    warn(
                        'Cut boundaries for parameter {}'
                        ' are not a two dimensional array'.format(key)
                    )

    def _warn_site_name(self):
        """Raise warnings if site_name is not the correct format

        Site names should be lowercase strings.
        """

        if not self.site_name.islower():
            warn(
                'pwv_kpno uses lowercase site names. The site name {} will be'
                ' saved as {}.'.format(self.site_name, self.site_name.lower())
            )

    def _warn_id_codes(self):
        """Raise warnings if SuomiNet ID codes are not the correct format

        SuomiNet ID codes should be four characters long and uppercase.
        """

        all_id_codes = self.sup_rec.copy()
        all_id_codes.append(self.primary_rec)
        for id_code in all_id_codes:
            if len(id_code) != 4:
                warn('ID is not of expected length 4: {}'.format(id_code))

            if not id_code.isupper():
                warn(
                    'SuomiNet ID codes should be uppercase. ID code {} will'
                    ' be saved as {}.'.format(id_code, id_code.upper())
                )

    def _create_config_dict(self):
        """Create a dictionary with config data for this site

        Returns:
            A dictionary storing site settings
        """

        config_data = dict()
        self._warn_data_cuts()
        config_data['data_cuts'] = self.data_cuts

        self._warn_site_name()
        config_data['site_name'] = self.site_name.lower()

        self._warn_id_codes()
        config_data['primary_rec'] = self.primary_rec.upper()
        config_data['sup_rec'] = [id_code.upper() for id_code in self.sup_rec]
        return config_data

    def save_to_dir(self, out_dir, overwrite=False):
        # type: (str) -> None
        """Create a custom config file <out_dir>/<self.site_name>.ecsv

        Args:
            out_dir    (str): The desired output directory
            overwrite (bool): Whether to overwrite an existing file
        """

        self._raise_unset_attributes()
        model = create_pwv_atm_model(mod_lambda=np.array(self.wavelengths),
                                     mod_cs=np.array(self.cross_sections),
                                     out_lambda=np.array(self.wavelengths))

        model.meta = self._create_config_dict()
        out_path = os.path.join(out_dir, self.site_name + '.ecsv')
        model.write(out_path, overwrite=overwrite)

    def __repr__(self):
        rep = '<ConfigBuilder site_name={}, primary_rec={}>'
        return rep.format(self.site_name, self.primary_rec)
