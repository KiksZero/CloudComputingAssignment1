import boto3

#Creating one single ec2 instance of the type t2.micro

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