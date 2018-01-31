import collections

InstanceType = collections.namedtuple(
    'InstanceType',
    [
        'size',
        'availability_zone',
        'tenancy',
        'product',
    ]
)

InstanceReservation = collections.namedtuple(
    'InstanceReservation',
    [
        'type',
        'count',
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

InstanceMatching = collections.namedtuple(
    'InstanceMatching',
    [
        'offering',
        'count_reserved',
        'count',
    ]
)
