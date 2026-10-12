from math import asin, cos, radians, sin, sqrt


def haversine_miles(lat1, lon1, lat2, lon2):
    radius_miles = 3958.7613

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )

    return 2 * radius_miles * asin(min(1.0, sqrt(a)))


def test_pilot_1243_original_geocode_is_incorrect():
    actual = (32.9299688, -112.6727971)
    returned = (33.539534, -112.373957)

    distance = haversine_miles(
        actual[0],
        actual[1],
        returned[0],
        returned[1],
    )

    assert distance > 40
