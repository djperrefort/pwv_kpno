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

"""This code calculates atmospheric transmission curves based on cross-section
files generated by the LSST project's phosim code and the Beer-Lambert Law. It
is heavily based on code written by Wei Hu in numIntwei_new.py.

This code is not called by any end user functions. The models generated by
this code  are already included in the pwv_kpno package. This code is included
for documentation purposes and for reference in future package development.
"""

import os

from astropy.table import Table
import numpy as np
import scipy.interpolate as interpolate

from ._settings import PHOSIM_DATA

__authors__ = 'Azalee Bostroem'
__copyright__ = 'Copyright 2016, Azalee Bostroem'
__editor__ = 'Daniel Perrefort'

__license__ = 'GPL V3'
__email__ = 'abostroem@gmail.com'
__status__ = 'Development'


def _load_cross_section(filename, x_fine):
    """Interpolate cross-section to fine wavelength grid (x_fine)

    Args:
        filename: name of cross-section file

    Returns:
        Cross-section data interpolated to input wavelength scale
    """

    cs = np.loadtxt(filename)
    y_func = interpolate.interp1d(cs[:, 0], cs[:, 1], kind='nearest')
    cs = np.transpose(np.array([x_fine, y_func(x_fine)]))
    return cs[:, :2]  # slice to the first two columns


def _construct_atm_sys(x_fine):
    """Create an array of interpolated cross section for H20, O3, and O2
    at each wavelength in the fine wavelength array. Cross sections
    are stacked into a single array

    Args:
        x_fine: fine wavelength array

    Returns:
        tuple with:
            array of cross-sections stacked together
    """

    filelist = ['h2ocs.txt', 'o3cs.txt', 'o2cs.txt']  # cross section in cm^2

    a_h2o = _load_cross_section(os.path.join(PHOSIM_DATA, filelist[0]), x_fine)
    a_o3 = _load_cross_section(os.path.join(PHOSIM_DATA, filelist[1]), x_fine)
    a_o2 = _load_cross_section(os.path.join(PHOSIM_DATA, filelist[2]), x_fine)

    atm_list = np.array([a_h2o, a_o3, a_o2])
    return atm_list


def _calculate_atm(atm_list, x_fine, xlf_dict, pint_list):
    """Calculate the atmospheric transmission

    Args:
        atm_list: array of cross-sections of H2O, O2, and O3
        x_fine: wavelength array
        xlf_dict: dictionary of values to be used to scale of p_int for
                      different levels of H2O, O2, and O3
        pint_list: list of initial p_int values

    Returns:
        transmission of all species
    """

    # The following code allows for the modeling for atmospheric
    # effects due to O2, O3, and H2O. We only use the code H2O,
    # and comment out the rest for future reference
    """
    # formula, x_fine in um / 0.5um # aerosol tau
    AOD = xlf_dict['tau'].reshape((1, 1, 1, len(xlf_dict['tau']), 1, 1)) * \
          (x_fine/0.5) ** \
          (-xlf_dict['index'].reshape((1, 1, 1, 1, len(xlf_dict['index']), 1)))

    # aerosol tau
    tau_aero = -AOD

    # O2 transmission
    # + -cross-section*pint*tune?*x1f
    o2_len = len(xlf_dict['o2'])
    tau_aero_o2 = tau_aero + (-atm_list[2, :, 1] * pint_list[2] *
                              xlf_dict['o2'].reshape((1, 1, o2_len, 1, 1, 1)))

    # X O3 transmission
    o3_len = len(xlf_dict['o3'])
    tau_aero_o3 = (-atm_list[1, :, 1] * pint_list[1] *
                   xlf_dict['o3'].reshape((1, o3_len, 1, 1, 1, 1)))
    tau_aero_o2_o3 = tau_aero_o2 + tau_aero_o3

    # X H2o transmission
    h2o_len = len(xlf_dict['h2o'])
    tau_aero_h2o = (-atm_list[0, :, 1] * pint_list[0] *
                    xlf_dict['h2o'].reshape((h2o_len, 1, 1, 1, 1, 1)))
    tau_aero_o2_o3_h2o = tau_aero_o2_o3 + tau_aero_h2o
    """

    # X H2o transmission
    h2o_len = len(xlf_dict['h2o'])
    tau_aero_o2_o3_h2o = (-atm_list[0, :, 1] * pint_list[0] *
                          xlf_dict['h2o'].reshape((h2o_len, 1, 1, 1, 1, 1)))

    return np.exp(tau_aero_o2_o3_h2o)


def _generate_atm_model(wl_start, wl_end, dispersion, pint_list, xlf_dict):
    """Generate a model of atmospheric absorption

    Args:
        wl_start: starting wavelength of model in angstroms
        wl_end: ending wavelength of model in angstroms
        dispersion: dispersion of model (angstroms/pix)

    Returns:
        atm_transmission: the atmospheric transmission
    """

    num_pts = (wl_end - wl_start)/float(dispersion)

    x_fine_ang = np.linspace(wl_start, wl_end, num_pts)
    x_fine = x_fine_ang / 10000.  # In microns

    atm_list = _construct_atm_sys(x_fine)
    atm_transmission = _calculate_atm(atm_list, x_fine, xlf_dict, pint_list)
    return x_fine_ang, atm_transmission


def write_atm_models(output_dir):
    """Uses the function _generate_atm_model to create an atmospheric
    model, and writes the results to disk as csv files in the directory
    output_dir. CSV files are named 'atm_trans_mod_VAL_pwv' where VAL
    is the PWV value in mm.

    Args:
        output_dir (str): The directory each generated file is written to
    """

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    NA = 6.02214129E23  # Avogadro's constant
    mol_cm_3 = NA / (18.0152 * 0.99997 * 10)  # Conversion to mol/cm^3

    # Integrated PWV
    # pint_h2o_norm=4.6331404996e+22  # 13.8595965622 mm
    pint_h2o_norm = 1.0  # Put all variation in xlf_dict['h2o']
    pint_o3_norm = 6.83830002464e+18  # 254 Dobson Units, 1 DU = 2.69e16
    pint_o2_norm = 4.51705326392e+24
    pint_list = [pint_h2o_norm, pint_o3_norm, pint_o2_norm]

    # If we decide to use the other elements in the atmospheric model then we
    # probably want to re-examine the values chosen here
    xlf_dict = {
        # 0.1 - 30.1 mm in units of mol/cm^3
        'h2o': np.arange(0.1, 31, 1) * mol_cm_3,

        'o3': np.array([1.0]),     # 20-50% DU
        'o2': np.array([1.]),      # 0.02%
        'tau': np.array([0.05]),   # aerosol tau
        'index': np.array([1.28])  # aerosol index
    }

    wl, atm_trans = _generate_atm_model(7000, 10000, 1, pint_list, xlf_dict)

    # Asserts that transmission is 100% for all wavelengths when PWV is 0
    out_table = Table(names=['wavelength', '00.0'],
                      data=[wl, [1 for i in wl]])

    for model_num, model in enumerate(xlf_dict['h2o']):
        temp_table = Table(data=[wl, atm_trans[model_num, 0, 0, 0, 0, :]],
                           names=['wavelength', 'transmission'])

        pwv_level = model / NA * (18.0152 * 0.99997 * 10)
        pwv_as_str = '{:.1f}'.format(pwv_level).zfill(4)
        temp_table.rename_column('transmission', pwv_as_str)
        out_table.add_column(temp_table[pwv_as_str])

    out_table.write(os.path.join(output_dir, 'atm_model.csv'), overwrite=True)
