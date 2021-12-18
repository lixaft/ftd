# pylint: disable=all
import ftd.datatype


def test_repr():
    """Test the representation of a vector."""
    vec = ftd.datatype.Vector(x=1, y=12, z=-2)
    assert repr(vec) == "<Vector (1, 12, -2)>"
    assert str(vec) == "(1, 12, -2)"


def test_classmethods():
    """Test the creation of a vector via the class methods."""
    vec = ftd.datatype.Vector.one()
    assert vec == ftd.datatype.Vector(1, 1, 1)
    vec = ftd.datatype.Vector.zero()
    assert vec == ftd.datatype.Vector(0, 0, 0)


def test_comparison():
    """Test the vector comparison."""
    vec = ftd.datatype.Vector(1, 2, 3)
    assert vec == ftd.datatype.Vector(1, 2, 3)
    assert not vec == ftd.datatype.Vector.one()
    assert vec != ftd.datatype.Vector.one()
    assert not vec != ftd.datatype.Vector(1, 2, 3)


def test_magnitude():
    """Test version magnitude computation."""
    assert ftd.datatype.Vector(1, 0, 0).magnitude() == 1
    assert ftd.datatype.Vector(10, 5, 10).magnitude() == 15


def test_normalize():
    """Test the vecot normalization."""
    vec = ftd.datatype.Vector(10, 10, 10)
    assert vec.normal().magnitude() == 1
    assert vec.normal() is not vec
    vec.normalize()
    assert vec.magnitude() == 1


def test_container():
    """Test the container methods."""
    vec = ftd.datatype.Vector(1, 2, 3)
    assert vec[0] == vec.x
    assert vec[1] == vec.y
    assert vec[2] == vec.z
    assert tuple(vec) == (1, 2, 3)
    assert list(vec) == [1, 2, 3]
