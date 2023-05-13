from flask import Flask, request
import math
import requests
import consul
import uuid
import time
import threading
import random

from rabbitmq_sidecar import RabbitMQSidecar

app = Flask(__name__)

port = int(input("Enter port number: "))
assert port

service_name = input("Enter node name: ")
assert service_name

# Connect to RabbitMQ
rabbitmq_sidecar = RabbitMQSidecar()
rabbitmq_sidecar.connect()

# Send a message to RabbitMQ
rabbitmq_sidecar.send_message('Hello, world!')

# Bully algorithm related variables
master_id = None
election_in_progress = False
service_registry = None
consul_client = consul.Consul()

def is_prime(num):
    if num <= 1:
        return False
    for i in range(2, int(math.sqrt(num))+1):
        if num % i == 0:
            return False
    return True

@app.route('/proposer-schedule', methods=['POST'])
def proposer_schedule():
    data = request.get_json()
    X_value = data["X_value"]
    num_ports = len(data["ports"])
    range_size = (X_value-1) // num_ports   # divide the range into equal parts for each port
    start = 1

    response = ""
    for i in range(num_ports):
        end = start + range_size   # calculate the end of the range for this port
        if i == num_ports - 1:
            end = X_value   # handle the last port which might have a larger range
        port_range = (start, end)
        url = f"http://localhost:{data['ports'][i]}/check-prime"
        response += f"http://localhost:{data['ports'][i]}/proposer-schedule has the number range in {start} to {end}\n"
        requests.post(url, json={"X_value": X_value, "range": port_range})
        start = end + 1   # update the start of the next range
    return response

@app.route('/check-prime', methods=['POST'])
def check_prime():
    data = request.get_json()
    port_range = data["range"]
    start, end = port_range
    response = ""
    for num in range(start, end+1):
        if is_prime(num):
            response += f"{num} is prime.\n"
        else:
            response += f"{num} is not prime.\n"
    return {"response": response}

def generate_service_id_id():
    service_id = uuid.uuid1().int >> 64
    return service_id

def wait_for_nodes(num_nodes):
    while True:
        try:
            services = consul_client.agent.services()
            if len(services) >= num_nodes:
                print("4 nodes started...")
                return
            # Wait for at least 4 nodes to start
            print(f"Waiting for 4 nodes to start...")
            time.sleep(30)
        except:
            time.sleep(10)
            print(f"No instances of {service_name} found in the catalog")

def election_timeout(max_id):
    global election_in_progress
    # Wait for some random amount of time before starting the election
    timeout = random.randint(5, 10)
    print(f"Waiting for {timeout} seconds before starting election...")
    time.sleep(timeout)

    # Start the election
    print("Starting Election...")
    election_in_progress = True
    if election_in_progress:
        # Find all nodes with higher IDs
        url = 'http://127.0.0.1:8500/v1/agent/services'
        response = requests.get(url)
        service_registry = response.json()
        higher_nodes = []
        # Iterate over all services to compare their IDs with 14548095516055048685
        for service_id, service_data in service_registry.items():
            try:
                if int(service_id) > int(service_id):
                    higher_nodes.append(service_id)
            except ValueError:
                pass  # Skip over keys that cannot be converted to integers

        if len(higher_nodes) == 0:
            # This node is the new master
            print("This node is the new master!")
            global master_id
            master_id = service_id
            # Add "role:master" tag to the master node
            url = f'http://127.0.0.1:8500/v1/agent/service/tag/role:master/service_id/{master_id}'
            requests.put(url)
            election_in_progress = False
            return
        else:
            # Send an election message to all higher nodes
            for node in higher_nodes:
                url = f"http://{node['Address']}:{node['ServicePort']}/start-election"
                requests.post(url)

@app.route('/start-election', methods=['POST'])
def start_election():
    global election_in_progress
    global master_id
    if election_in_progress:
        # Wait for election to finish
        while election_in_progress:
            time.sleep(1)
        # Start the election
        print(f"Election initiated by {get_service_id()}")
        election_in_progress = True
        # Find all nodes with higher IDs
        higher_nodes = []
        for service in service_registry.catalog.service(service_name)[1]:
            if int(service["ServiceID"]) > int(get_service_id()):
                higher_nodes.append(service)
        if len(higher_nodes) == 0:
            # This node is the new master
            print("This node is the new master!")
            master_id = get_service_id()
            election_in_progress = False
            return "Election finished."
        else:
            # Send an election message to all higher nodes
            for node in higher_nodes:
                url = f"http://{node['Address']}:{node['ServicePort']}/start-election"
                requests.post(url)
            return "Election in progress."


def get_service_id():
    service_id = consul_client.agent.service.service_id(service_name)
    return service_id


def get_max_id_nodename():
    import requests
    url = 'http://127.0.0.1:8500/v1/agent/services'
    response = requests.get(url)
    services = response.json()

    max_id = None
    max_service = None

    for service_id, service_data in services.items():
        service_name = service_data['Service']
        service_id = int(service_id)
        if max_id is None or service_id > max_id:
            max_id = service_id
            max_service = service_name

    print("Max ID Service Name:", max_service)
    print("Max ID Service ID:", max_id)
    return max_service, max_id


def init():
    wait_for_nodes(4)
    print("starting the election for the first time...")
    # # Start the election if this node has the highest ID
    max_service, max_id = get_max_id_nodename()
    if max_service == service_name:
        threading.Thread(target=election_timeout, args=(max_id,)).start()

timer_thread1 = threading.Timer(15, init)
timer_thread1.start()

if __name__ == '__main__':
    # Register with Consul
    service_port = port
    service_id = generate_service_id_id()
    consul_client.agent.service.register(
        name=service_name,
        service_id=str(service_id),
        address='localhost',
        port=service_port,
        check=consul.Check.tcp('localhost', service_port, interval='10s')
    )
    time.sleep(5)
    # Start Flask app
    app.run(host='127.0.0.1', port=port)