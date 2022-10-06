import boto3



def create_ec2_instance():
    print("creating instance")
    instance_ec2 =  boto3.client("ec2")
    instance_ec2.run_instances(
        ImageId = "ami-08c40ec9ead489470",
        MinCount = 1,
        MaxCount = 1,
        InstanceType = "t2.micro",
        KeyName = "vockey",
        UserData = """#!/bin/bash 
        
        sudo apt update -y
        sudo apt upgrade -y
        sudo apt install -y python3-venv
        su ubuntu
        cd /home/ubuntu 
        mkdir flask_application && cd flask_application
        python3 -m venv venv
        source venv/bin/activate
        pip install Flask
        sudo curl -o app.py "https://raw.githubusercontent.com/KiksZero/CloudComputingAssignment1/main/test_flask.py?token=GHSAT0AAAAAABYR4YEBKHLNEFR426URVIIQYZ7H6HQ"
        sudo /home/ubuntu/flask_application/venv/bin/flask run --host=0.0.0.0 --port=80 
        """
         )

create_ec2_instance()