import uuid
import requests
import threading
from random import randint
from multiprocessing import Value
from flask import jsonify
from run import initiate_node, check_master_health
from acceptor import get_learner_from_service_registry
from proposer import get_acceptors_from_service_registry
from common import get_ports_of_nodes

counter = Value('i', 0)

def generate_node_id():
    """
    Generates a unique 64-bit integer node ID using the UUID1 algorithm.

    Returns:
        A 64-bit integer node ID generated using the UUID1 algorithm.
    """
    node_id = uuid.uuid1().int >> 64
    return node_id

def is_prime_number(random_number, start, end):
    if random_number <= 1:
        return f'{random_number} number'
    else:
        for number in range(start, end):
            if random_number % number == 0 and random_number != number:
                print(f"{random_number} is divisible by {number}. {random_number} is not a prime number")
                return f"{random_number} is divisible by {number}. {random_number} is not a prime number"
        print(f"{random_number} is a prime number")
        return f"{random_number} is a prime number"

# This method is used to register the service in the service registry
def register_service(name, port, node_id):
    url = "http://localhost:8500/v1/agent/service/register"
    data = {
        "Name": name,
        "ID": str(node_id),
        "port": port,
        "check": {
            "name": "Check Counter health %s" % port,
            "tcp": "localhost:%s" % port,
            "interval": "10s",
            "timeout": "1s"
        }
    }
    put_request = requests.put(url, json=data)
    return put_request.status_code

# ----------------- API functions ---------------

def get_node_details_util(node):
    master_node = node.master
    node_id_node = node.node_id
    election_node = node.election
    node_name_node = node.node_name
    port_node = node.port
    return jsonify({'node_name': node_name_node, 'node_id': node_id_node, 'master': master_node,
                    'election': election_node, 'port': port_node}), 200

def response_node_util(data, node):
    incoming_node_id = data['node_id']
    self_node_id = node.node_id
    if self_node_id > incoming_node_id:
        threading.Thread(target=initiate_node, args=[False]).start()
        node.election = False
    return jsonify({'Response': 'OK'}), 200

def announce_master_util(data, node):
    master = data['master']
    node.master = master
    print('master is %s ' % master)
    return jsonify({'response': 'OK'}), 200

'''
When nodes are sending the election message to the higher nodes, all the requests comes to this proxy. As the init
method needs to execute only once, it will forward exactly one request to the responseAPI. 
'''
def proxy_util(data, node):
    with counter.get_lock():
        counter.value += 1
        unique_count = counter.value
    url = f'http://localhost:{node.port}/response'
    if unique_count == 1:
        requests.post(url, json=data)

def proposers_util(data, node):
    check_master_health(node)
    print(data)
    return jsonify({'response': 'OK'}), 200


'''
This API receives the messages from proposers. If the message say the number is  prime, it will forward to the
leaner without re-verifying. If it says the number is not prime, it will verify the number by its own and send
the message to the learner. 
'''
def prime_result_util(data):
    print('prime result from proposer', data['primeResult'])
    url = get_learner_from_service_registry()
    result = data['primeResult']
    result_string = {"result": result}
    print('Sending the result to learner: %s' % url)
    if 'is a prime number' in result:
        requests.post(url, json=result_string)
    else:
        print("Verifying the result as it says not a prime number......")
        number = int(result.split()[0])
        verified_result = is_prime_number(number, 2, number - 1)
        verified_result_string = {"result": verified_result}
        requests.post(url, json=verified_result_string)
    return jsonify({'response': 'OK'}), 200

'''
This API receives a number to be checked along with its range to be divided from the master node. Upon the sent 
data, the calculation will be done and pass the result to a randomly selected acceptor. 
'''
def proposer_schedule_util(data):
    print(data)
    start = data['start']
    end = data['end']
    random_number = data['random_number']

    print('Checking %s number for prime....' % random_number)
    result_string = is_prime_number(random_number, start, end)

    data = {"primeResult": result_string}
    print(data)
    url_acceptor = get_acceptors_from_service_registry()
    print('Sending the result to a random acceptor %s' % url_acceptor)
    requests.post(url_acceptor, json=data)
    return jsonify({'response': 'OK'}), 200


'''
This API receives the messages from acceptors and verify if there are any messages saying that number is not
prime. If so it will decide that the number is not prime. Else it will decide the number is prime. 
'''
def final_result_util(data):
    # an array to capture the messages that receive from acceptors
    learner_result_array = []
    number = data['result'].split()[0]
    print('prime result from acceptor', data['result'])

    learner_result_array.append(data['result'])
    print(learner_result_array)

    count = 0
    for each_result in learner_result_array:
        if 'not a prime number' in each_result:
            count = count + 1

    if count > 0:
        final = '%s is not prime' % number
        print(final)
    else:
        final = '%s is prime' % number
        print(final)

    print('-------Final Result-----------')
    number_of_msgs = len(learner_result_array)
    print('Number of messages received from acceptors: %s' % number_of_msgs)
    print('Number of messages that says number is not prime: %s' % count)
    print(final)

    return jsonify({'response': final}), 200




