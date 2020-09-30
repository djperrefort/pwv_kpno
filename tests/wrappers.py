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

"""Utilities used to ensure a stable and predictable testing environment"""

import functools
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union

TEST_DATA_DIR = Path(__file__).parent / 'testing_data'
TEST_DATA_CONFIG = TEST_DATA_DIR / 'test_data.yml'


# Todo: Wrap setUp and tearDown methods as well
class TestWithCleanEnv:
    """Context manager and decorator for running tests in a clean environment

    Clears all environmental variables and sets ``SUOMINET_DIR`` to a temporary
    directory.
    """

    def __init__(self, data_path: Union[str, Path] = None):
        """Clears all environmental variables and set the ``SUOMINET_DIR``
        variable

        Value for ``SUOMINET_DIR`` defaults to a temporary directory. Can be
        used as a context manager, function decorator, or class decorator. If
        used as a class decorator, only methods named ``test_*`` are wrapped.

        Args:
            data_path: Optional path to set as ``SUOMINET_DIR``
        """

        if isinstance(data_path, Path):
            data_path = str(data_path)

        self._data_path = data_path

    def __call__(self, obj):
        # Wrap the passed object or callable

        # Decide whether we should wrap ``obj`` as a class or function
        if isinstance(obj, type):
            return self._decorate_class(obj)

        return self._decorate_callable(obj)

    def __enter__(self):
        # Store a copy of environmental variables and clear the environment

        self._old_environ = dict(os.environ)
        os.environ.clear()

        if self._data_path:  # Use user defined path
            os.environ['SUOMINET_DIR'] = self._data_path

        else:
            self._temp_dir = TemporaryDirectory()
            os.environ['SUOMINET_DIR'] = self._temp_dir.name

    def __exit__(self, *args):
        # Restore the original environment

        os.environ.clear()
        os.environ.update(self._old_environ)

        if not self._data_path:  # If there is no user defined path
            self._temp_dir.cleanup()

    def _decorate_callable(self, func: callable) -> callable:
        # Decorates a callable

        @functools.wraps(func)
        def inner(*args, **kwargs):
            with TestWithCleanEnv(self._data_path):
                return func(*args, **kwargs)

        return inner

    def _decorate_class(self, wrap_class: type) -> type:
        # Decorates class methods
        # Method will be decorated only if it name begins with ``test_``

        for attr_name in dir(wrap_class):
            # Skip attributes without correct prefix
            if not (attr_name.startswith('test_')  or attr_name in ('setUp')):
                continue

            # Skip attributes that are not callable
            attr = getattr(wrap_class, attr_name)
            if callable(attr):
                setattr(wrap_class, attr_name, self._decorate_callable(attr))

        return wrap_class
