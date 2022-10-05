import boto3



def create_ec2_instance():
    print("creating instance")
    instance_ec2 =  boto3.client("ec2")
    instance_ec2.run_instances(
        ImageId = "ami-08c40ec9ead489470",
        MinCount = 1,
        MaxCount = 1,
        InstanceType = "t2.micro",
        KeyName = "vockey"   
         )

create_ec2_instance()