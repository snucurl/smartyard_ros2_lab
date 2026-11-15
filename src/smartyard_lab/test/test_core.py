import math
from types import SimpleNamespace as Obj
from smartyard_lab.core import check_transport, advance, validate_value

def fixtures():
    return (Obj(job_id='JOB_1', block_id='B1', source_zone='A', target_zone='B'),
            Obj(block_id='B1', zone_id='A', load_t=40.0, wind_speed_mps=6.0, route_blocked=False))

def assess(**changes):
    req, sensor = fixtures()
    options = dict(sensor_age=0.1, timeout=3.0, max_load=50.0, max_wind=10.0)
    for k, v in changes.items():
        if hasattr(sensor, k): setattr(sensor, k, v)
        elif hasattr(req, k): setattr(req, k, v)
        else: options[k] = v
    return check_transport(req, sensor, **options)

def test_normal():
    assert assess() == (True, 'OK', 30.0)

def test_threshold_inclusive():
    assert assess(load_t=50.0, wind_speed_mps=10.0)[0]

def test_overload():
    assert assess(load_t=50.01)[1] == 'OVERLOAD'

def test_wind():
    assert assess(wind_speed_mps=10.01)[1] == 'HIGH_WIND'

def test_stale_sensor():
    assert assess(sensor_age=3.01)[1] == 'SENSOR_STALE'

def test_missing_sensor():
    req, _ = fixtures()
    assert check_transport(req, None, 0, 3, 50, 10)[1] == 'SENSOR_STALE'

def test_stale_vehicle():
    assert assess(vehicle_age=3.01)[1] == 'VEHICLE_STALE'

def test_busy():
    assert assess(vehicle_busy=True)[1] == 'VEHICLE_BUSY'

def test_obstacle():
    assert assess(route_blocked=True)[1] == 'ROUTE_BLOCKED'

def test_wrong_zone():
    assert assess(zone_id='B')[1] == 'BLOCK_OR_ZONE_MISMATCH'

def test_unknown_route():
    assert assess(target_zone='C')[1] == 'UNKNOWN_ROUTE'

def test_empty_job():
    assert assess(job_id=' ')[1] == 'EMPTY_JOB_ID'

def test_invalid_sensor():
    for value in [float('nan'), float('inf'), -1.0]:
        assert assess(load_t=value)[1] == 'INVALID_SENSOR_VALUE'

def test_motion_clamps():
    assert advance(29.5, 2.0, 1.0, 30.0) == 30.0

def test_piecewise_motion():
    assert advance(advance(0.0, 1.0, 10.0, 30.0), 0.5, 40.0, 30.0) == 30.0

def test_parameter_range_and_type():
    rules = {'speed': (float, 0.2, 2.0)}
    assert validate_value('speed', 0.5, rules)[0]
    for value in [-1.0, float('nan'), 1, True]:
        assert not validate_value('speed', value, rules)[0]
