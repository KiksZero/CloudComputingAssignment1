#!/bin/bash

sudo apt update -y
sudo apt upgrade -y
sudo apt install -y python3-venv
su ubuntu
cd /home/ubuntu
mkdir flask_application && cd flask_application
echo $INSTANCE_ID > id
python3 -m venv venv
source venv/bin/activate
pip install Flask
sudo curl -o app.py "https://raw.githubusercontent.com/KiksZero/CloudComputingAssignment1/main/app.py"
sudo /home/ubuntu/flask_application/venv/bin/flask run --host=0.0.0.0 --port=80
