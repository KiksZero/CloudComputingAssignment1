import boto3
#---------SETTINGS----------------
imageId = 'ami-08c40ec9ead489470' # ubuntu 22.04
keyName = 'vockey'

#----------SCRIPT-----------------
ec2_client =  boto3.client("ec2")
with open('init.sh', 'r') as file:
    initScript = file.read()
ec2_resource = boto3.resource("ec2")

#Creating a VPC for our cidrblock on AWS
vpc = ec2_resource.create_vpc(CidrBlock='172.31.0.0/16')
vpc.wait_until_available()

internetgateway = ec2_resource.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

ec2_client.modify_vpc_attribute(VpcId = vpc.id, EnableDnsSupport = {'Value': True})
ec2_client.modify_vpc_attribute(VpcId = vpc.id, EnableDnsHostnames = {'Value': True})
#Creating a security group that only allows HTTP
securitygroup = ec2_resource.create_security_group(GroupName='HTTP-ONLY', Description='only allow HTTP traffic', VpcId=vpc.id)
securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=80, ToPort=80)

#Creating the 2 subnets that are used in the loadbalancer
subnetA = ec2_client.create_subnet(
    AvailabilityZoneId = 'use1-az2',
    CidrBlock = '172.31.48.0/20',
    VpcId = vpc.id
)


subnetB = ec2_client.create_subnet(
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

<<<<<<< HEAD
   instance_ec2.run_instances(
=======
   ec2_client.run_instances(
>>>>>>> 6a23a92063b378576c5a38f28313f0002f38c943
       ImageId = imageId,
       MinCount = 1,
       MaxCount = 1,
       InstanceType = instanceType,
       KeyName = keyName,
<<<<<<< HEAD
      UserData = initScript.replace('$INSTANCE_ID', str(i))
=======
       UserData = initScript.replace('$INSTANCE_ID', str(i))
>>>>>>> 6a23a92063b378576c5a38f28313f0002f38c943
   )


client = boto3.client('elbv2')
client.create_target_group( Name='Cluster1', Protocol='HTTP',  Port=80, VpcId=vpc.id)
client.create_target_group( Name='Cluster2', Protocol='HTTP',  Port=80, VpcId=vpc.id)
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


