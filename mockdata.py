from mytypes import *

reserved_instances = (
    [   InstanceReservation(type=InstanceType(size='t2.medium', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), count=30),
        InstanceReservation(type=InstanceType(size='c4.xlarge', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), count=15),
        InstanceReservation(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), count=30),
        InstanceReservation(type=InstanceType(size='c4.xlarge', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), count=15)]
)
#reserved_instances = None

ondemand_instances = (
    [   (   InstanceType(size='c5.large', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='c4.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='t2.small', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 2),
        (   InstanceType(size='c5.large', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='c5.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m5.xlarge', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), 39),
        (   InstanceType(size='c5.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m4.2xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m4.4xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='i3.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='t2.small', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='c5.large', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='c5.large', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='c5.2xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 2),
        (   InstanceType(size='t2.micro', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m5.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 43),
        (   InstanceType(size='m4.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 2),
        (   InstanceType(size='m5.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 29),
        (   InstanceType(size='c5.xlarge', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m3.medium', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m4.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 8),
        (   InstanceType(size='m3.medium', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='c5.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m4.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 6),
        (   InstanceType(size='m5.4xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='p2.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='m4.xlarge', availability_zone='us-east-1e', tenancy='default', product='Linux/UNIX'), 2),
        (   InstanceType(size='m5.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 27),
        (   InstanceType(size='m3.medium', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), 3),
        (   InstanceType(size='m4.large', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1),
        (   InstanceType(size='c4.2xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), 1)]
)
instance_types = None

instance_offerings = (
    [   InstanceOffering(type=InstanceType(size='t2.medium', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.0464, cost_reserved_worst=0.0331, cost_reserved_best=0.017427701674277016),
        InstanceOffering(type=InstanceType(size='m5.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.192, cost_reserved_worst=0.141, cost_reserved_best=0.07370624048706241),
        InstanceOffering(type=InstanceType(size='c5.large', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.085, cost_reserved_worst=0.062, cost_reserved_best=0.031012176560121764),
        InstanceOffering(type=InstanceType(size='c5.xlarge', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.17, cost_reserved_worst=0.123, cost_reserved_best=0.061986301369863016),
        InstanceOffering(type=InstanceType(size='c4.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.199, cost_reserved_worst=0.145, cost_reserved_best=0.07800608828006088),
        InstanceOffering(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1e', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.2, cost_reserved_worst=0.1425, cost_reserved_best=0.07519025875190259),
        InstanceOffering(type=InstanceType(size='t2.small', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.023, cost_reserved_worst=0.0165, cost_reserved_best=0.008713850837138508),
        InstanceOffering(type=InstanceType(size='m3.medium', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.067, cost_reserved_worst=0.05, cost_reserved_best=0.026141552511415526),
        InstanceOffering(type=InstanceType(size='c5.large', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.085, cost_reserved_worst=0.062, cost_reserved_best=0.031012176560121764),
        InstanceOffering(type=InstanceType(size='c5.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.17, cost_reserved_worst=0.123, cost_reserved_best=0.061986301369863016),
        InstanceOffering(type=InstanceType(size='m3.medium', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.067, cost_reserved_worst=0.05, cost_reserved_best=0.026141552511415526),
        InstanceOffering(type=InstanceType(size='c5.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.17, cost_reserved_worst=0.123, cost_reserved_best=0.061986301369863016),
        InstanceOffering(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.2, cost_reserved_worst=0.1425, cost_reserved_best=0.07519025875190259),
        InstanceOffering(type=InstanceType(size='m5.4xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.768, cost_reserved_worst=0.564, cost_reserved_best=0.2947869101978691),
        InstanceOffering(type=InstanceType(size='m5.xlarge', availability_zone='us-east-1f', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.192, cost_reserved_worst=0.141, cost_reserved_best=0.07370624048706241),
        InstanceOffering(type=InstanceType(size='c5.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.17, cost_reserved_worst=0.123, cost_reserved_best=0.061986301369863016),
        InstanceOffering(type=InstanceType(size='m4.2xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.4, cost_reserved_worst=0.285, cost_reserved_best=0.1504185692541857),
        InstanceOffering(type=InstanceType(size='m4.4xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.8, cost_reserved_worst=0.5699, cost_reserved_best=0.3007990867579909),
        InstanceOffering(type=InstanceType(size='i3.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.312, cost_reserved_worst=0.246, cost_reserved_best=0.1319634703196347),
        InstanceOffering(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.2, cost_reserved_worst=0.1425, cost_reserved_best=0.07519025875190259),
        InstanceOffering(type=InstanceType(size='p2.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.9, cost_reserved_worst=0.706, cost_reserved_best=0.3995053272450533),
        InstanceOffering(type=InstanceType(size='t2.small', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.023, cost_reserved_worst=0.0165, cost_reserved_best=0.008713850837138508),
        InstanceOffering(type=InstanceType(size='c5.large', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.085, cost_reserved_worst=0.062, cost_reserved_best=0.031012176560121764),
        InstanceOffering(type=InstanceType(size='c5.large', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.085, cost_reserved_worst=0.062, cost_reserved_best=0.031012176560121764),
        InstanceOffering(type=InstanceType(size='c5.2xlarge', availability_zone='us-east-1d', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.34, cost_reserved_worst=0.246, cost_reserved_best=0.12401065449010655),
        InstanceOffering(type=InstanceType(size='c4.xlarge', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.199, cost_reserved_worst=0.145, cost_reserved_best=0.07800608828006088),
        InstanceOffering(type=InstanceType(size='m5.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.192, cost_reserved_worst=0.141, cost_reserved_best=0.07370624048706241),
        InstanceOffering(type=InstanceType(size='t2.micro', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.0116, cost_reserved_worst=0.0083, cost_reserved_best=0.004375951293759513),
        InstanceOffering(type=InstanceType(size='m5.xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.192, cost_reserved_worst=0.141, cost_reserved_best=0.07370624048706241),
        InstanceOffering(type=InstanceType(size='m3.medium', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.067, cost_reserved_worst=0.05, cost_reserved_best=0.026141552511415526),
        InstanceOffering(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.2, cost_reserved_worst=0.1425, cost_reserved_best=0.07519025875190259),
        InstanceOffering(type=InstanceType(size='m4.large', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.1, cost_reserved_worst=0.0712, cost_reserved_best=0.037595129375951296),
        InstanceOffering(type=InstanceType(size='c4.2xlarge', availability_zone='us-east-1c', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.398, cost_reserved_worst=0.29, cost_reserved_best=0.15509893455098936),
        InstanceOffering(type=InstanceType(size='m4.xlarge', availability_zone='us-east-1b', tenancy='default', product='Linux/UNIX'), cost_ondemand=0.2, cost_reserved_worst=0.1425, cost_reserved_best=0.07519025875190259)]
)
#instance_offerings = None
