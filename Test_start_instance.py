import boto3
#---------SETTINGS----------------
imageId = 'ami-08c40ec9ead489470' # ubuntu 22.04
keyName = 'vockey'

#----------SCRIPT-----------------
instance_ec2 =  boto3.client("ec2")
with open('init.sh', 'r') as file:
    initScript = file.read()
ec2_resource = boto3.resource("ec2")

#Creating a VPC for our cidrblock on AWS
vpc = ec2_resource.create_vpc(CidrBlock='172.31.0.0/16')
vpc.wait_until_available()

internetgateway = ec2_resource.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

instance_ec2.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
instance_ec2.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )
#Creating a security group that only allows HTTP
securitygroup = ec2_resource.create_security_group(GroupName='HTTP-ONLY', Description='only allow HTTP traffic', VpcId=vpc.id)
securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=80, ToPort=80)

#Creating the 2 subnets that are used in the loadbalancer
subnetA = instance_ec2.create_subnet(
    AvailabilityZoneId = 'use1-az2',
    CidrBlock = '172.31.48.0/20',
    VpcId = vpc.id
)


subnetB = instance_ec2.create_subnet(
    AvailabilityZoneId = 'use1-az4',
    CidrBlock = '172.31.16.0/20',
    VpcId = vpc.id
)

for i in range(9):
    if i < 4:
        instanceType = 't2.large'
    else:
        instanceType = 'm4.large'

    #instanceType = 't2.micro'
    print("creating instance, type: " + instanceType + " no." + str(i))

    instance_ec2.run_instances(
        ImageId = imageId,
        MinCount = 1,
        MaxCount = 1,
        InstanceType = instanceType,
        KeyName = keyName,
        UserData = initScript.replace('$INSTANCE_ID', str(i))
    )


client = boto3.client('elb')
response = client.create_load_balancer(
    LoadBalancerName='LoadBalancer1',
    Listeners=[
        {
            'Protocol': 'http',
            'LoadBalancerPort': 80,
            'InstanceProtocol': 'http',
            'InstancePort': 80
        },
    ],
    Subnets=[
        subnetA['Subnet']['SubnetId'],
        subnetB['Subnet']['SubnetId']
    ],
    SecurityGroups=[
        securitygroup.id,
    ],
    
)
