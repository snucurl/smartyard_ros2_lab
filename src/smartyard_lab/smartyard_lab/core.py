"""ROS-independent rules; the values describe a teaching model only."""
import math

ROUTES = {('A', 'B'): 30.0, ('B', 'A'): 30.0}

def check_transport(request, sensor, sensor_age, timeout, max_load, max_wind,
                    vehicle_busy=False, vehicle_age=0.0):
    if not request.job_id.strip():
        return False, 'EMPTY_JOB_ID', 0.0
    distance = ROUTES.get((request.source_zone, request.target_zone))
    if distance is None:
        return False, 'UNKNOWN_ROUTE', 0.0
    if sensor is None or sensor_age > timeout:
        return False, 'SENSOR_STALE', distance
    if not math.isfinite(sensor.load_t) or not math.isfinite(sensor.wind_speed_mps):
        return False, 'INVALID_SENSOR_VALUE', distance
    if sensor.load_t <= 0.0 or sensor.wind_speed_mps < 0.0:
        return False, 'INVALID_SENSOR_VALUE', distance
    if request.block_id != sensor.block_id or request.source_zone != sensor.zone_id:
        return False, 'BLOCK_OR_ZONE_MISMATCH', distance
    if sensor.load_t > max_load:
        return False, 'OVERLOAD', distance
    if sensor.wind_speed_mps > max_wind:
        return False, 'HIGH_WIND', distance
    if sensor.route_blocked:
        return False, 'ROUTE_BLOCKED', distance
    if vehicle_age > timeout:
        return False, 'VEHICLE_STALE', distance
    if vehicle_busy:
        return False, 'VEHICLE_BUSY', distance
    return True, 'OK', distance

def advance(distance, speed, dt, total):
    if not all(math.isfinite(x) for x in (distance, speed, dt, total)):
        raise ValueError('non-finite motion input')
    if min(distance, speed, dt, total) < 0:
        raise ValueError('negative motion input')
    return min(total, distance + speed * dt)

def validate_value(name, value, rules):
    rule = rules.get(name)
    if rule is None:
        return True, ''
    kind, low, high = rule
    if type(value) is not kind:
        return False, f'{name}: expected {kind.__name__}'
    if kind is float:
        if not math.isfinite(value) or not low <= value <= high:
            return False, f'{name}: allowed range [{low}, {high}]'
    if kind is str and not value.strip():
        return False, f'{name}: must not be empty'
    return True, ''
