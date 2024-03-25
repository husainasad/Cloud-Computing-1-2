This repository contains steps and key notes to develop and deploy a simple distributed and scalable web application using EC2, SQS and S3. <br>
The web application consists of :<br>
* Web Server: The web server would receive user requests, push the input to request SQS, pull the output from response SQS, and finally return the response to the user.
* App Server: The app server(s) would pull input from request sqs, process the requests, and finally push the output to response SQS.
* SQS (input and output): The SQS would enable decoupling between the web and app servers, allowing them to work asynchronously and scale independently.
* S3: To store the requests input and response outputs for sanity check.

The web server would contain a controller logic that scales the app servers based on the amount of requests pending in the request SQS.<br>
The architecture of the application is as follows:<br>
![CC-Project1-Part2-Architecture](https://github.com/husainasad/Cloud-Computing-1-2/assets/32503674/a939f54b-cb07-4dc9-9d88-f1605efc9b44)

## Step 1: Create Web Server and App Server Applications
The web server would be a FastAPI application. The app server can be developed as a python script running continuously. <br>

Fast API is supported on python 3.8+ versions </br>
The application can either be run using uvicorn. Command:
```
uvicorn {server file name}:app --host 0.0.0.0 --port 8000 --reload --workers=k
```
--host parameter (optional): binds the application server with machine IP (especially useful for EC2) </br>
--port number: port to run the application on </br>
--reload (optional): useful for development purposes, behaves as an auto server start on code change </br>
--workers (optional): can specify number of workers for concurrency </br>

## Step 2: Create SQS Queues
The SQS queues for web and app servers can be created by running the 'createSQS.py' script. </br>

## Step 3: Create S3 Buckets
The S3 buckets for app servers can be created by running the 'createS3.py' script. </br>

## Step 4: Create EC2 Instances
The EC2 instances for web and app servers can be created by running the 'createEC2.py' script. </br>

### Project Setup in EC2
Setting up the project in EC2 involves updating existing packages, pulling project from GitHub, creating virtual environment, installing relevant libraries before running the server code. </br>
To make this process automatic, the setup commands are saved in the '*-instance-script' and passed to the EC2 creation script as user data. </br>
Due to the different requirement from the servers, a different user data script would be used for instance creation. i.e. web-instance-script for web server and app-instance-script for app-server

## Step 5: Create App Server Scaling Instances
Instead of having a single app server to process requests, we would scale the app servers by increasing and decreasing the running servers based on the scaling logic.</br>
The ideal way to scale applications would be to create and delete app server instances. <br>
However, to optimize (and hardcode) the process, we can create a set number of instances and start and stop the required servers (instead of create and delete).<br>
The 'createScaledInstances.py' script would create the required number of app server instances based on the AMI of the original app server.<br>
So, before running this script, make sure to create the AMI from the app server and update in 'config' file.

## Deployed Application
The above mentioned scripts help create the required infrastructure of the application. </br>
Furthermore, since the command to run the server is added inside the boot files, the server will run automatically even after every bootup. </br>
This will save us an extra step to SSH into the instance and manually start the server and keep the process running. </br>
This way we are able to create a constantly running server without any need for manual server set up.

## Step 6: Test with Fast API doc
The created APIs can be tested on https://url:port/docs

## Steps 7: Test with Workload Generator
Workload Generator simulates a client side and sends requests to the server. The code matches the server responses and helps in verifying the correctness and efficiency of code logic. </br>
Command to test:
```
python ./Resources/workload_generator/workload_generator.py --num_request 100  --url http://url:port/ --image_folder "./Resources/dataset/face_images_1000/"  --prediction_file "./Resources/dataset/Classification Results on Face Dataset (1000 images).csv"
```
More information on workload generator can be found in the associated readme.
