import boto3
with open('init.sh', 'r') as file:
    initScript = file.read()
#Creating one single ec2 instance of the type t2.micro
instance_ec2 =  boto3.client("ec2")

for i in range(9):
    if i < 4:
        instanceType = 't2.large'
    else:
        instanceType = 'm4.large'

    #instanceType = 't2.micro'
    def create_ec2_instance():
        print("creating instance, type: " + instanceType + " no." + str(i))
        instance_ec2.run_instances(
            ImageId = "ami-08c40ec9ead489470",
            MinCount = 1,
            MaxCount = 1,
            InstanceType = instanceType,
            KeyName = "vockey",
            UserData = initScript.replace('$INSTANCE_ID', str(i))
             )

    create_ec2_instance()