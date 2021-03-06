"""Provide utilities related to mathematica."""
from __future__ import absolute_import, division

import logging
import math

LOG = logging.getLogger(__name__)


def _check_type(obj, type_):
    """Check the type of an object."""
    if not isinstance(obj, type_):
        raise TypeError("The object {} must be a type {}.".format(obj, type_))


class Vector(object):
    # pylint: disable=invalid-name
    """Three dimensional vector.

    Arguments:
        x (float): The x component of the vector.
        y (float): The y component of the vector.
        z (float): The z component of the vector.
    """

    __slots__ = ["_x", "_y", "_z"]

    PRECISION = 5
    TOLERANCE = 0.001

    def __repr__(self):
        return "<Vector ({}, {}, {})>".format(self._x, self._y, self._z)

    # Unary operator ---
    def __pos__(self):
        return Vector(+self.x, +self.y, +self.z)

    def __neg__(self):
        """Return a negative version of the vector.

        Examples:
            >>> v = Vector(1, 2, 3)
            >>> -v
            <Vector (-1, -2, -3)>
        """
        return Vector(-self.x, -self.y, -self.z)

    def __abs__(self):
        """Return an absolute version of the vector.

        Examples:
            >>> v = Vector(1, -2, 3)
            >>> abs(v)
            <Vector (1, 2, 3)>
        """
        return Vector(abs(self.x), abs(self.y), abs(self.z))

    def __round__(self, ndigits=0):
        """Return a rounded version of the vector.

        Examples:
            >>> v = Vector(1.123, 2.234, 3.345)
            >>> round(v, 1)
            <Vector (1.1, 2.2, 3.3)>
        """
        return Vector(
            round(self.x, ndigits),
            round(self.y, ndigits),
            round(self.z, ndigits),
        )

    def __ceil__(self):
        return Vector(
            math.ceil(self.x),
            math.ceil(self.y),
            math.ceil(self.z),
        )

    def __floor__(self):
        return Vector(
            math.floor(self.x),
            math.floor(self.y),
            math.floor(self.z),
        )

    def __trunc__(self):
        return Vector(
            math.trunc(self.x),
            math.trunc(self.y),
            math.trunc(self.z),
        )

    # Conversion ---
    def __str__(self):
        return str(tuple(self))

    # Arithmetic operator ---
    def __add__(self, vector):
        _check_type(vector, Vector)
        return Vector(self.x + vector.x, self.y + vector.y, self.z + vector.z)

    def __sub__(self, vector):
        _check_type(vector, Vector)
        return Vector(self.x - vector.x, self.y - vector.y, self.z - vector.z)

    def __mul__(self, scalar):
        _check_type(scalar, (float, int))
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar):
        _check_type(scalar, (float, int))
        return Vector(self.x / scalar, self.y / scalar, self.z / scalar)

    def __xor__(self, vector):
        _check_type(vector, Vector)
        return Vector(
            self.y * vector.z - self.z * vector.y,
            self.z * vector.x - self.x * vector.z,
            self.x * vector.y - self.y * vector.x,
        )

    # comparison operator
    def __eq__(self, vector):
        _check_type(vector, Vector)
        return self.x == vector.x and self.y == vector.y and self.z == vector.z

    def __ne__(self, vector):
        _check_type(vector, Vector)
        return self.x != vector.x or self.y != vector.y or self.z != vector.z

    def __ge__(self, vector):
        _check_type(vector, Vector)
        return self.magnitude() >= vector.magnitude()

    def __gt__(self, vector):
        _check_type(vector, Vector)
        return self.magnitude() > vector.magnitude()

    def __le__(self, vector):
        _check_type(vector, Vector)
        return self.magnitude() <= vector.magnitude()

    def __lt__(self, vector):
        _check_type(vector, Vector)
        return self.magnitude() < vector.magnitude()

    # Container type ---
    def __getitem__(self, key):
        """Allow access to components via the container synthax.

        Examples:
            >>> v = Vector(1, 2, 3)
            >>> v[0] == v["x"] == 1
            True
            >>> v[1] == v["y"] == 2
            True
            >>> v[2] == v["z"] == 3
            True
            >>> v[:2]
            (1, 2)
        """
        if key in (0, "x"):
            return self.x
        if key in (1, "y"):
            return self.y
        if key in (2, "z"):
            return self.z
        if isinstance(key, slice):
            return tuple(self[i] for i in range(*key.indices(len(self))))
        msg = "Vector of length 3. The index {} is out of range."
        raise KeyError(msg.format(key))

    def __setitem__(self, key, value):
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        elif key == 2:
            self.z = value
        msg = "Vector of length 3. The index {} is out of range."
        raise KeyError(msg.format(key))

    def __iter__(self):
        return iter((self._x, self._y, self._z))

    def __len__(self):
        return 3

    # Constructor ---
    def __copy__(self):
        return Vector(self.x, self.z, self.z)

    def __init__(self, x=0, y=0, z=0):
        self._x = round(x, self.PRECISION)
        self._y = round(y, self.PRECISION)
        self._z = round(z, self.PRECISION)

    # Class methods ---
    @classmethod
    def zero(cls):
        """Build a vector with all its components set to zero."""
        return cls(0, 0, 0)

    @classmethod
    def one(cls):
        """Build a vector with all its components set to one."""
        return cls(1, 1, 1)

    # Read write properties ---
    @property
    def x(self):
        """float: The x component of the vector."""
        return self._x

    @x.setter
    def x(self, value):
        self._x = round(value, self.PRECISION)

    @property
    def y(self):
        """float: The y component of the vector."""
        return self._y

    @y.setter
    def y(self, value):
        self._y = round(value, self.PRECISION)

    @property
    def z(self):
        """float: The z component of the vector."""
        return self._z

    @z.setter
    def z(self, value):
        self._z = round(value, self.PRECISION)

    # Public methods ---
    def length(self):
        """Compute the length of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normal(self):
        """Return a normalized copy of self.

        Returns:
            Vector: A normalized copy of the vector.
        """
        vector = self.copy()
        vector.normalize()
        return vector

    def normalize(self):
        """Normalize self to make its magnitude egal to 1."""
        magnetude = self.magnitude()
        self.x = self.x / magnetude
        self.y = self.y / magnetude
        self.z = self.z / magnetude

    # Aliases ---
    magnitude = length
    cross = __xor__
    dot = __mul__
    copy = __copy__
