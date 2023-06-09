import requests
from common import get_ports_of_nodes, check_health_of_the_service
import math
import random


# After deciding the master, it checks the active nodes by checking with the service registry.
def check_active_nodes(master):
    registered_nodes = []
    response = requests.get('http://127.0.0.1:8500/v1/agent/services')
    nodes = response.json()
    for each_service in nodes:
        service = nodes[each_service]['Service']
        registered_nodes.append(service)
    registered_nodes.remove(master)
    health_status = []
    for each in registered_nodes:
        if check_health_of_the_service(each) == 'passing':
            health_status.append(each)
    print('Tha active nodes are: ', health_status)
    return health_status


# This method is used to decide the roles for the other nodes.
def decide_roles(node_array):
    print(f"\n####\n{node_array}\n####")
    roles = {}
    for i in range(0,2):
        node = node_array[i]
        role = 'Acceptor'
        key = node
        value = role
        roles[key] = value
    learner = node_array[2]
    roles[learner] = 'Learner'
    for i in range(3, len(node_array)):
        node = node_array[i]
        role = 'Proposer'
        key = node
        value = role
        roles[key] = value
    print('roles', roles)
    return roles


# This method is used to inform each node about their role.
def inform_roles(roles, master):
    ports_array = get_ports_of_nodes()
    del ports_array[master]
    combined = {key: (roles[key], ports_array[key]) for key in roles}
    print('combined', combined)

    data_acceptor = {"role": "acceptor"}
    data_learner = {"role": "learner"}
    data_proposer = {"role": "proposer"}

    for each in combined:
        if combined[each][0] == 'Acceptor':
            url = 'http://localhost:%s/acceptor' % combined[each][1]
            print(url)
            requests.post(url, json=data_acceptor)
        elif combined[each][0] == 'Learner':
            url = 'http://localhost:%s/learner' % combined[each][1]
            print(url)
            requests.post(url, json=data_learner)
        else:
            url = 'http://localhost:%s/proposer' % combined[each][1]
            print(url)
            requests.post(url, json=data_proposer)
    return combined


# this method is used to schedule the range that they should start dividing based on the number.
def schedule_work_for_proposers(combined):
    count = 0
    range_array_proposers = []
    for each in combined:
        if combined[each][0] == 'Proposer':
            range_array_proposers.append(combined[each][1])
            count = count + 1
    print('range_array', range_array_proposers)

    random_number = read_number_from_file()
    proposer_list_len = len(range_array_proposers)
    if proposer_list_len > 0:
        number_range = math.floor(random_number / proposer_list_len)
    else:
        # handle the case where proposer_list_len is zero
        number_range = 0
    start = 2

    for each in range(proposer_list_len):
        divide_range = {
            "start": start,
            "end": start + number_range,
            "random_number": random_number
        }
        print(divide_range)
        url = 'http://localhost:%s/proposer-schedule' % range_array_proposers[each]
        print(url)
        requests.post(url, json=divide_range)

        start += number_range + 1


def read_number_from_file():
    file_name = "numbers.txt"
    with open(file_name, 'r') as f:
        lines = f.read().splitlines()
        random_number = int(random.choice(lines))
    return random_number


def get_node_ids(node_name):
    response = requests.get('http://127.0.0.1:8500/v1/agent/services')
    nodes = response.json()

    for each in nodes:
        if nodes[each]['Service'] == node_name:
            node_id = nodes[each]['ID']
    return node_id


# This method is used to update the Service Registry after deciding the roles.
def update_service_registry(roles):
    url = "http://localhost:8500/v1/agent/service/register"
    for each in roles:
        role_data = {
            "Name": each,
            "ID": get_node_ids(each),
            "Port": roles[each][1],
            "Meta": {"Role": roles[each][0]},
            "check": {
                "name": "Check Counter health %s" % roles[each][1],
                "tcp": "localhost:%s" % roles[each][1],
                "interval": "10s",
                "timeout": "1s"
            }
        }
        requests.put(url, json=role_data)
