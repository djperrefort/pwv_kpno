#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides modeling for the effects of atmospheric absorption
due to precipitable water vapor (PWV) on a black body.

For full documentation on a function use the builtin Python `help` function
or see https://mwvgroup.github.io/pwv_kpno/.

An Incomplete Guide to Getting Started:

    To determine the SED of a black body under the influence of atmospheric
    effects due to a known PWV concentration (in mm):

      >>> from pwv_kpno import black_body
      >>>
      >>> temp = 8000  # Black Body temperature in Kelvin
      >>> wavelengths = np.arange(7000, 10000, 100) # Wavelengths in Angstrom
      >>> pwv = 17  # Integrated PWV concentration in mm
      >>>
      >>> black_body.sed(temp, wavelengths, pwv)


    To determine the magnitude of a black body both with and without
    atmospheric effects:

    >>> band = (7000, 10000) # Units of Angstrom
    >>> mag_without_atm, mag_with_atm = black_body.magnitude(temp, band, pwv)


    To determine the residual error in the zero point of a photometric image
    due to PWV:

    >>> reference_star_temp = 4000
    >>> other_star_temps = 10000
    >>> bias = zp_bias(reference_star_temp, other_star_temps, band, pwv)
"""

from astropy import units as u
from astropy.constants import c
from astropy.modeling.blackbody import blackbody_lambda
import numpy as np

from pwv_kpno._transmission import transmission_pwv


def sed(temp, wavelengths, pwv):
    """Return the flux of a black body under the influence of pwv absorption

     Flux is returned in units of ergs / (angstrom * cm2 * s)

     Args:
         temp          (float): The desired temperature of the black body
         wavelengths (ndarray): An array like object containing wavelengths
         pwv           (float): The PWV concentration along line of sight in mm

     Returns:
         An array of flux values in units of ergs / (angstrom * cm2 * s)
     """

    bb_sed = blackbody_lambda(wavelengths, temp)
    bb_sed *= (4 * np.pi * u.sr)  # Integrate over angular coordinates

    if pwv > 0:
        transmission = transmission_pwv(pwv)
        resampled_transmission = np.interp(wavelengths,
                                           transmission['wavelength'],
                                           transmission['transmission'])

        bb_sed *= resampled_transmission

    return bb_sed


def magnitude(temp, band, pwv):
    """Return the magnitude of a black body with and without pwv absorption

    Magnitudes are calculated relative to a zero point of 3631 Jy

    Args:
        temp (float): The temperature of the desired black body
        band (tuple): Tuple with the beginning and end wavelengths of the
                       desired band in angstroms
        pwv  (float): The PWV concentration along line of sight in mm

    Returns:
        The magnitude of the desired black body WITHOUT H2O absorption
        The magnitude of the desired black body WITH H2O absorption
    """

    wavelengths = np.arange(band[0], band[1])
    lambda_over_c = (np.median(band) * u.AA) / c

    flux = sed(temp, wavelengths, 0)
    flux *= lambda_over_c.cgs

    flux_pwv = sed(temp, wavelengths, pwv)
    flux_pwv *= lambda_over_c.cgs

    zero_point = (3631 * u.jansky).to(u.erg / u.cm ** 2)
    int_flux = np.trapz(x=wavelengths, y=flux) * u.AA
    int_flux_transm = np.trapz(x=wavelengths, y=flux_pwv) * u.AA

    magnitude = -2.5 * np.log10(int_flux / zero_point)
    magnitude_transm = -2.5 * np.log10(int_flux_transm / zero_point)

    return magnitude.value, magnitude_transm.value


def zp_bias(ref_temp, cal_temp, band, pwv):
    """Calculate the residual error in the photometric zero point due to PWV

    Using a black body approximation, calculate the residual error in the zero
    point of a photometric image cause by not considering the PWV transmission
    function.

    Args:
        ref_temp (float): The temperature of a star used to calibrate the image
        cal_temp (float): The temperature of another star in the same image to
                           calculate the error for
        band     (tuple): Tuple specifying the beginning and end points
                           of the desired band in angstroms
        pwv      (float): The PWV concentration along line of sight

    Returns:
        The residual error in the second star's magnitude
    """

    # Values for reference star
    ref_mag, ref_mag_atm = magnitude(ref_temp, band, pwv)
    ref_zero_point = ref_mag - ref_mag_atm

    # Values for star being calibrated
    cal_mag, cal_mag_atm = magnitude(cal_temp, band, pwv)
    cal_zero_point = cal_mag - cal_mag_atm

    bias = cal_zero_point - ref_zero_point
    return bias
