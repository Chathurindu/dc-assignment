# Consensus Based Prime Number Deciding Distributed System

The overall application is a distributed consensus algorithm using the Paxos protocol. It has been built as a Flask Application, which exposes APIs that can be used by different nodes in the distributed system to communicate with each other. The Flask Application runs on a specified port number, which is obtained from the command-line arguments. The node name is also obtained from the command-line arguments, which is used to generate a unique node ID.
The application uses RabbitMQServer as a sidecar to handle logs. RabbitMQ is a message broker that enables communication between distributed applications. In this application, RabbitMQServer is used to send and receive messages between different nodes in the distributed system.
Consul has been used as the service register to register each node in the distributed system. Service registration is an essential part of the distributed system, which enables each node to discover and communicate with other nodes in the system. Consul provides a simple and flexible way to register and discover services in a distributed system.

1. As a pre requirement you have to install RabitMQ and create a python virtual envirement and install requirements.txt
```
pip install -r requirements.txt
```

2. First you need to download Consul and run it.
```
consul agent -dev
```
3. Since this implmenetation each node runs in the same code base, you have to give node name and port as user inputs. This cluster required minimum 5 nodes with the same code base. You need to run the each node in a new terminal. 

Node1
```
 python app.py 5001 n1
```

Node2
```
 python app.py 5002 n2
```

Node3
```
 python app.py 5003 n3
```

Node4
```
 python app.py 5004 n4
```

Node5
```
 python app.py 5005 n5
```