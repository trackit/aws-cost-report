import collections

InstanceType = collections.namedtuple(
    'InstanceType',
    [
        'size',
        'availability_zone',
        'tenancy',
        'product',
        'vpc',
    ]
)

InstanceTypeWithProfile = collections.namedtuple(
    'InstanceTypeWithProfile',
    [
        'profile',
        'instance_type',
    ]
)

InstanceReservation = collections.namedtuple(
    'InstanceReservation',
    [
        'type',
        'cost_hourly',
        'cost_upfront',
    ]
)

InstanceReservationCount = collections.namedtuple(
    'InstanceReservationCount',
    [
        'instance_reservation',
        'count',
        'count_used'
    ]
)

InstanceOffering = collections.namedtuple(
    'InstanceOffering',
    [
        'type',
        'cost_ondemand',
        'cost_reserved_worst',
        'cost_reserved_best',
    ]
)

InstanceOfferingCount = collections.namedtuple(
    'InstanceOfferingCount',
    [
        'instance_offering',
        'count',
        'count_reserved',
    ]
)
