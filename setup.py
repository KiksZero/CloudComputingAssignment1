import boto3
import time
import requests
import datetime

# ---------SETTINGS----------------
image_id = 'ami-08c40ec9ead489470'  # ubuntu 22.04
key_name = 'vockey'
instance_type_cluster_1 = 'm4.large'
instance_count_cluster_1 = 4
url_cluster_1 = '/cluster1'
instance_type_cluster_2 = 't2.large'
instance_count_cluster_2 = 5
url_cluster_2 = '/cluster2'
vpc_cidr_block = '172.31.0.0/16'
availability_zone_id_subnet_a = 'use1-az2'
availability_zone_id_subnet_b = 'use1-az4'
cidr_block_subnet_a = '172.31.48.0/20'
cidr_block_subnet_b = '172.31.16.0/20'
cluster_1_requests = 1000
cluster_2_requests_before_timeout = 500
cluster_2_requests_after_timeout = 1000

# ----------SCRIPT-----------------
ec2_client = boto3.client("ec2")
ec2_resource = boto3.resource("ec2")
elbv2_client = boto3.client('elbv2')

with open('init_instance.sh', 'r') as file:
    instance_init_script = file.read()

# Creating a VPC for our cidrblock on AWS
print('Creating VPC, Internet gateway and Route table')
vpc = ec2_resource.create_vpc(CidrBlock=vpc_cidr_block)
vpc.wait_until_available()
ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsSupport={'Value': True})
ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsHostnames={'Value': True})

# Creating Internet gateway and Route table
internet_gateway = ec2_resource.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)
route_table = vpc.create_route_table()
route = route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internet_gateway.id)

# Creating a security group that only allows HTTP
security_group = ec2_resource.create_security_group(GroupName='HTTP-ONLY', Description='only allow HTTP traffic',
                                                    VpcId=vpc.id)
security_group.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=80, ToPort=80)

# Creating the 2 subnets that are used in the ELB
print('Creating subnets in zones ' + availability_zone_id_subnet_a + ' and ' + availability_zone_id_subnet_b)
subnet_a = ec2_client.create_subnet(
    AvailabilityZoneId=availability_zone_id_subnet_a,
    CidrBlock=cidr_block_subnet_a,
    VpcId=vpc.id
)

ec2_client.modify_subnet_attribute(
    MapPublicIpOnLaunch={
        'Value': True
    },
    SubnetId=subnet_a['Subnet']['SubnetId']
)

subnet_b = ec2_client.create_subnet(
    AvailabilityZoneId=availability_zone_id_subnet_b,
    CidrBlock=cidr_block_subnet_b,
    VpcId=vpc.id
)

ec2_client.modify_subnet_attribute(
    MapPublicIpOnLaunch={
        'Value': True
    },
    SubnetId=subnet_b['Subnet']['SubnetId']
)
route_table.associate_with_subnet(SubnetId=subnet_a['Subnet']['SubnetId'])
route_table.associate_with_subnet(SubnetId=subnet_b['Subnet']['SubnetId'])

# Create cluster 1 instances
print("Creating instances for cluster 1, type: " + instance_type_cluster_1)
instances_cluster_1 = ec2_client.run_instances(
    ImageId=image_id,
    MinCount=instance_count_cluster_1,
    MaxCount=instance_count_cluster_1,
    InstanceType=instance_type_cluster_1,
    KeyName=key_name,
    NetworkInterfaces=[
        {
            'SubnetId': subnet_a['Subnet']['SubnetId'],
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [security_group.id]
        }
    ],
    UserData=instance_init_script.replace('$_INSTANCE_TYPE', instance_type_cluster_1).replace('$_CLUSTER_URL',
                                                                                              url_cluster_1)
)
targets_cluster_1 = [{'Id': instance['InstanceId']} for instance in instances_cluster_1['Instances']]

# Create cluster 2 instances
print("Creating instances for cluster 2, type: " + instance_type_cluster_2)
instances_cluster_2 = ec2_client.run_instances(
    ImageId=image_id,
    MinCount=instance_count_cluster_2,
    MaxCount=instance_count_cluster_2,
    InstanceType=instance_type_cluster_2,
    KeyName=key_name,
    NetworkInterfaces=[
        {
            'SubnetId': subnet_b['Subnet']['SubnetId'],
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [security_group.id]
        }
    ],
    UserData=instance_init_script.replace('$_INSTANCE_TYPE', instance_type_cluster_2).replace('$_CLUSTER_URL',
                                                                                              url_cluster_2)
)
targets_cluster_2 = [{'Id': instance['InstanceId']} for instance in instances_cluster_2['Instances']]

# Creating clusters
print('Creating clusters')
cluster_1 = elbv2_client.create_target_group(Name='Cluster1', Protocol='HTTP', Port=80, VpcId=vpc.id)
elbv2_client.modify_target_group(
    TargetGroupArn=cluster_1['TargetGroups'][0]['TargetGroupArn'],
    HealthCheckProtocol='HTTP',
    HealthCheckPath=url_cluster_1
)
cluster_2 = elbv2_client.create_target_group(Name='Cluster2', Protocol='HTTP', Port=80, VpcId=vpc.id)
elbv2_client.modify_target_group(
    TargetGroupArn=cluster_2['TargetGroups'][0]['TargetGroupArn'],
    HealthCheckProtocol='HTTP',
    HealthCheckPath=url_cluster_2
)

# Creating ELB and ELB Listener
print('Creating ELB and ELB Listener')
elb = elbv2_client.create_load_balancer(
    Name='LoadBalancer1',
    Subnets=[
        subnet_a['Subnet']['SubnetId'],
        subnet_b['Subnet']['SubnetId']
    ],
    SecurityGroups=[
        security_group.id,
    ],
)
elb_listener = elbv2_client.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': cluster_1['TargetGroups'][0]['TargetGroupArn'],
            'Type': 'forward',
        },
    ],
    LoadBalancerArn=elb['LoadBalancers'][0]['LoadBalancerArn'],
    Port=80,
    Protocol='HTTP',
)

# Adding rules for the ELB listener
print('Adding rules for the ELB listener')
elbv2_client.create_rule(
    ListenerArn=elb_listener['Listeners'][0]['ListenerArn'],
    Conditions=[
        {
            'Field': 'path-pattern',
            'Values': ['/cluster1']
        }
    ],
    Priority=123,
    Actions=[
        {
            'Type': 'forward',
            'TargetGroupArn': cluster_1['TargetGroups'][0]['TargetGroupArn'],
        }
    ]
)

elbv2_client.create_rule(
    ListenerArn=elb_listener['Listeners'][0]['ListenerArn'],
    Conditions=[
        {
            'Field': 'path-pattern',
            'Values': ['/cluster2']
        }
    ],
    Priority=124,
    Actions=[
        {
            'Type': 'forward',
            'TargetGroupArn': cluster_2['TargetGroups'][0]['TargetGroupArn'],
        }
    ]
)

# Waiting for all instances to get into "running" state
print('Waiting for instances to get into running state...')
running_instances_count = 0
while running_instances_count < 9:
    running_instances_count = 0
    for target in (targets_cluster_1 + targets_cluster_2):
        instance_resource = ec2_resource.Instance(target['Id'])
        if instance_resource.state['Name'] == 'running':
            running_instances_count += 1
    time.sleep(2)

print('Hooray, all instances are running!')

# Register running instances to target groups
print('Registering targets')
elbv2_client.register_targets(
    TargetGroupArn=cluster_1['TargetGroups'][0]['TargetGroupArn'],
    Targets=targets_cluster_1
)

elbv2_client.register_targets(
    TargetGroupArn=cluster_2['TargetGroups'][0]['TargetGroupArn'],
    Targets=targets_cluster_2
)

print('DONE!')

# Waiting for all targets to get into "healthy" state
print('Waiting for targets to get into healthy state...')
healthy_count = 0
while healthy_count < 9:
    healthy_count = 0
    cluster_1_health = elbv2_client.describe_target_health(
        TargetGroupArn=cluster_1['TargetGroups'][0]['TargetGroupArn'],
        Targets=targets_cluster_1
    )
    for target in cluster_1_health['TargetHealthDescriptions']:
        if target['TargetHealth']['State'] == 'healthy':
            healthy_count += 1
    cluster_2_health = elbv2_client.describe_target_health(
        TargetGroupArn=cluster_2['TargetGroups'][0]['TargetGroupArn'],
        Targets=targets_cluster_2
    )
    for target in cluster_2_health['TargetHealthDescriptions']:
        if target['TargetHealth']['State'] == 'healthy':
            healthy_count += 1
    time.sleep(5)

print('Hooray, all targets are healthy!')

# sending 1000 requests to cluster 1
print('Sending ' + str(cluster_2_requests_before_timeout + cluster_2_requests_after_timeout) + ' requests to cluster 1')
for i in range(1, cluster_1_requests):
    url =  'http://'+ elb['LoadBalancers'][0]['DNSName'] + '/cluster1'
    headers = {'content-type': 'application/json'}
    r = requests.get(url, headers=headers)

# sending 1500 requests to cluster 2 with 60s sleep
print('Sending ' + str(cluster_2_requests_before_timeout + cluster_2_requests_after_timeout) + ' requests to cluster 2 with 60s sleep')
for i in range(1,requests_before_timeout):
    url2 = 'http://'+ elb['LoadBalancers'][0]['DNSName'] + '/cluster2'
    headers = {'content-type': 'application/json'}
    r2 = requests.get(url2, headers=headers)
time.sleep(60)
for i in range(1,requests_after_timeout):
    url2 = 'http://'+ elb['LoadBalancers'][0]['DNSName'] + '/cluster2'
    headers = {'content-type': 'application/json'}
    r2 = requests.get(url2, headers=headers)


cloudwatch = boto3.client('cloudwatch')

# get metrics for each instance for cluster 1
metrics = ['CPUUtilization', 'NetworkIn', 'NetworkOut']
for instance in targets_cluster_1:
    for metric in metrics:
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'test2',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': metric,
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance['Id']
                                },
                            ]
                        },
                        'Period': 60,
                        'Stat': 'Average'
                    },
                },
            ],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(days=1),
            EndTime=datetime.datetime.utcnow(),
        )
        print(metric, instance['Id'])
        print(response['MetricDataResults'][0]['Values'])

# get metrics for each instance for cluster 2
metrics = ['CPUUtilization', 'NetworkIn', 'NetworkOut']
for instance in targets_cluster_2:
    for metric in metrics:
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'test2',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': metric,
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance['Id']
                                },
                            ]
                        },
                        'Period': 60,
                        'Stat': 'Average'
                    },
                },
            ],
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(days=1),
            EndTime=datetime.datetime.utcnow(),
        )
        print(metric, instance['Id'])
        print(response['MetricDataResults'][0]['Values'])
