import consul
import requests
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

# Set up Consul client
consul_client = consul.Consul()

# Constants
BASE_PORT = 8080
NUM_NODES = 5
PRIME_API_ENDPOINT = '/proposer-schedule'

# Global variables
node_id = None
leader_id = None
nodes = []
election_timeout = 3  # seconds

def register_endpoints(app):
    app.add_url_rule('/', view_func=handle_leader, methods=['POST'])
    app.add_url_rule(PRIME_API_ENDPOINT, view_func=proposer_schedule, methods=['GET'])


def get_node_id(port):
    return port - BASE_PORT + 1

def get_port(node_id):
    return BASE_PORT + node_id - 1

def register_node(node_id):
    port = get_port(node_id)
    consul_client.agent.service.register(name=f'node{node_id}', service_id=str(port), port=port)

def deregister_node(node_id):
    consul_client.agent.service.deregister(service_id=str(get_port(node_id)))

def get_nodes():
    services = consul_client.agent.services()
    nodes = [int(service_id) for service_id in services.keys() if services[service_id]['Service'] == 'node']
    nodes.sort()
    return nodes

def start_election():
    global leader_id
    leader_id = None

    if not nodes:
        return

    election_start_time = time.time()

    higher_nodes = [n for n in nodes if n > node_id]

    for n in higher_nodes:
        requests.get(f'http://localhost:{get_port(n)}/election')

    while time.time() - election_start_time < election_timeout:
        if leader_id:
            return
        time.sleep(0.1)

    # No leader elected, declare self as leader
    leader_id = node_id
    for n in nodes:
        if n != node_id:
            requests.post(f'http://localhost:{get_port(n)}', json={'leader_id': leader_id})

@app.route('/election', methods=['GET'])
def handle_election():
    if leader_id is not None:
        requests.post(f'http://localhost:{get_port(request.json["node_id"])}', json={'leader_id': leader_id})
    return jsonify({'ok': True})

@app.route('/', methods=['POST'])
def handle_leader():
    global leader_id
    leader_id = request.json['leader_id']
    return jsonify({'ok': True})

@app.route(PRIME_API_ENDPOINT)
def proposer_schedule():
    global leader_id

    if node_id != leader_id:
        return jsonify({'error': 'I am not the leader!'})

    lower_range = (node_id - 1) * 1000 + 1
    upper_range = node_id * 1000

    factors = [[] for _ in range(lower_range, upper_range + 1)]

    for i in range(2, upper_range + 1):
        if factors[i - lower_range]:
            continue
        for j in range(i * 2, upper_range + 1, i):
            factors[j - lower_range].append(i)

    prime_nums = []
    for i in range(lower_range, upper_range + 1):
        if not factors[i - lower_range]:
            prime_nums.append(i)
            print(f"Node {node_id} found prime number: {i}")

    return jsonify({'prime_numbers': prime_nums})

if __name__ == '__main__':
    # Get all nodes from Consul
    nodes = get_nodes()
    # Get the node ID for this instance
    node_id = get_node_id(8080)
    # Set the initial leader ID to None
    leader_id = None
    # Create a Flask app instance
    app = Flask(__name__)
    # Register the endpoints with Flask
    register_endpoints(app)

    # Start the periodic election process
    def election():
        # Send election message to all nodes with higher IDs
        for node in nodes:
            if node['node_id'] > node_id:
                send_election_message(node['address'], node_id)
        # Wait for a certain period to receive "ok" messages
        time.sleep(5)
        # Check if a leader has been elected
        if leader_id is None:
            # Declare this node as the leader
            leader_id = node_id
            # Send leader message to all nodes with lower IDs
            for node in nodes:
                if node['node_id'] < node_id:
                    send_leader_message(node['address'], node_id)
        else:
            # Wait for a leader message from the node with highest ID
            time.sleep(5)
            if leader_id != node_id:
                # Send election message again
                send_election_message(get_node_address(leader_id, nodes), node_id)

    # Start the Flask app
    app.run(host='0.0.0.0', port=8080, debug=True)

    # Start the periodic election process as a separate thread
    threading.Thread(target=lambda: schedule.every(10).seconds.do(election).run()).start()

