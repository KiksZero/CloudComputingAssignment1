import boto3
import time

# ---------SETTINGS----------------
imageId = 'ami-08c40ec9ead489470'  # ubuntu 22.04
keyName = 'vockey'
instanceTypeCluster1 = 'm4.large'
instanceCountCluster1 = 4
instanceTypeCluster2 = 't2.large'
instanceCountCluster2 = 5

# ----------SCRIPT-----------------
ec2_client = boto3.client("ec2")
with open('init.sh', 'r') as file:
    initScript = file.read()
ec2_resource = boto3.resource("ec2")

# Creating a VPC for our cidrblock on AWS
vpc = ec2_resource.create_vpc(CidrBlock='172.31.0.0/16')
vpc.wait_until_available()

internetgateway = ec2_resource.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsSupport={'Value': True})
ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsHostnames={'Value': True})
# Creating a security group that only allows HTTP
securitygroup = ec2_resource.create_security_group(GroupName='HTTP-ONLY', Description='only allow HTTP traffic',
                                                   VpcId=vpc.id)
securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=80, ToPort=80)

# Creating the 2 subnets that are used in the loadbalancer
subnetA = ec2_client.create_subnet(
    AvailabilityZoneId='use1-az2',
    CidrBlock='172.31.48.0/20',
    VpcId=vpc.id
)

ec2_client.modify_subnet_attribute(
    MapPublicIpOnLaunch={
        'Value': True
    },
    SubnetId = subnetA['Subnet']['SubnetId']
)

subnetB = ec2_client.create_subnet(
    AvailabilityZoneId='use1-az4',
    CidrBlock='172.31.16.0/20',
    VpcId=vpc.id
)

ec2_client.modify_subnet_attribute(
    MapPublicIpOnLaunch={
        'Value': True
    },
    SubnetId = subnetB['Subnet']['SubnetId']
)

# Create cluster 1 instances
print("Creating instances for cluster 1, type: " + instanceTypeCluster1)
instancesCluster1 = ec2_client.run_instances(
    ImageId=imageId,
    MinCount=instanceCountCluster1,
    MaxCount=instanceCountCluster1,
    InstanceType=instanceTypeCluster1,
    KeyName=keyName,
    NetworkInterfaces=[
        {
            'SubnetId': subnetA['Subnet']['SubnetId'],
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [securitygroup.id]
        }
    ],
    UserData=initScript.replace('$_INSTANCE_TYPE', instanceTypeCluster1)
)
cluster1Targets = [{'Id': instance['InstanceId']} for instance in instancesCluster1['Instances']]

# Create cluster 2 instances
print("Creating instances for cluster 2, type: " + instanceTypeCluster2)
instancesCluster2 = ec2_client.run_instances(
    ImageId=imageId,
    MinCount=instanceCountCluster2,
    MaxCount=instanceCountCluster2,
    InstanceType=instanceTypeCluster2,
    KeyName=keyName,
    NetworkInterfaces=[
        {
            'SubnetId': subnetB['Subnet']['SubnetId'],
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [securitygroup.id]
        }
    ],
    UserData=initScript.replace('$_INSTANCE_TYPE', instanceTypeCluster2)
)
cluster2Targets = [{'Id': instance['InstanceId']} for instance in instancesCluster2['Instances']]

client = boto3.client('elbv2')
Cluster1 = client.create_target_group(Name='Cluster1', Protocol='HTTP', Port=8080, VpcId=vpc.id)
Cluster2 = client.create_target_group(Name='Cluster2', Protocol='HTTP', Port=8081, VpcId=vpc.id)
elb = client.create_load_balancer(
    Name='LoadBalancer1',
    Subnets=[
        subnetA['Subnet']['SubnetId'],
        subnetB['Subnet']['SubnetId']
    ],
    SecurityGroups=[
        securitygroup.id,
    ],
)
Cluster1Listener = client.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': Cluster1['TargetGroups'][0]['TargetGroupArn'],
            'Type': 'forward',
        },
    ],
    LoadBalancerArn=elb['LoadBalancers'][0]['LoadBalancerArn'],
    Port=8080,
    Protocol='HTTP',
)
Cluster2Listener = client.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': Cluster2['TargetGroups'][0]['TargetGroupArn'],
            'Type': 'forward',
        },
    ],
    LoadBalancerArn=elb['LoadBalancers'][0]['LoadBalancerArn'],
    Port=8081,
    Protocol='HTTP',
)

# Wait for all instances to get into "running" state
print('Waiting for instances to get into running state...')
runnningCount = 0
while runnningCount < 9:
    runnningCount = 0
    for target in (cluster1Targets + cluster2Targets):
        instanceResource = ec2_resource.Instance(target['Id'])
        if instanceResource.state['Name'] == 'running':
            runnningCount += 1
    time.sleep(2)

print('Hooray, all instances are running!')

client.register_targets(
    TargetGroupArn=Cluster1['TargetGroups'][0]['TargetGroupArn'],
    Targets=cluster1Targets
)

client.register_targets(
    TargetGroupArn=Cluster2['TargetGroups'][0]['TargetGroupArn'],
    Targets=cluster2Targets
)
