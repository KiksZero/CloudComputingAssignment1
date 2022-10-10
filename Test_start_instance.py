import boto3
#---------SETTINGS----------------
imageId = 'ami-08c40ec9ead489470' # ubuntu 22.04
keyName = 'vockey'

#----------SCRIPT-----------------
instance_ec2 =  boto3.client("ec2")
with open('init.sh', 'r') as file:
    initScript = file.read()

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
