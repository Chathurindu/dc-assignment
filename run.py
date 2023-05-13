import random
import requests
import time
import threading

from common import get_ports_of_nodes, get_higher_nodes, election, announce, ready_for_election, get_details, check_health_of_the_service
from master import check_active_nodes, decide_roles, inform_roles, schedule_work_for_proposers, \
    update_service_registry

def initiate_node(service_register_status, node,  wait=True):
    if service_register_status == 200:
        ports_of_all_nodes = get_ports_of_nodes()
        del ports_of_all_nodes[node.node_name]
        # exchange node details with each node
        node_details = get_details(ports_of_all_nodes)
        if wait:
            timeout = random.randint(5, 15)
            time.sleep(timeout)
            print(f'timeouting in {timeout} seconds')

        # checks if there is an election on going
        election_ready = ready_for_election(ports_of_all_nodes, node.election, node.master)
        if election_ready or not wait:
            print(f'Starting election in: {node.node_name}')
            node.election = True
            higher_nodes_array = get_higher_nodes(node_details, node.node_id)
            print('higher node array', higher_nodes_array)
            if len(higher_nodes_array) == 0:
                node.master = True
                node.election = False
                announce(node.node_name)
                print('**********End of election**********************')
            else:
                election(higher_nodes_array, node.node_id)
        else:
            print("master has been already selected...")
        master_run(node)
    else:
        print('Service registration is not successful')


# No node spends idle time, they always checks if the master node is alive in each 60 seconds.
def check_master_health(node):
    threading.Timer(60.0, check_master_health, args=(node,)).start()
    health = check_health_of_the_service(node.master)
    if health == 'crashed':
        initiate_node()
    else:
        print('master is alive')

# after deciding the master, this method has the work that is done by the master node.
def master_run(node):
    active_nodes_array = check_active_nodes(node.node_name)
    if len(active_nodes_array) >= 4:
        roles = decide_roles(active_nodes_array)
        combined = inform_roles(roles, node.node_name)
        update_service_registry(combined)
        schedule_work_for_proposers(combined)

        proposer_count = 0
        for each in roles:
            if roles[each] == 'Proposer':
                proposer_count = proposer_count + 1
        print('proposer_count', proposer_count)
        proposer_count_data = {"proposer_count": proposer_count}

        for each in combined:
            if combined[each][0] == 'Learner':
                url = 'http://localhost:%s/learner' % combined[each][1]
                print(url)
                requests.post(url, json=proposer_count_data)
    else:
        message = f"Currently {len(active_nodes_array)} active node(s) excluding master node. Minimum required nodes are 4. Please create other nodes."
        print(message)
