import json
import requests

# get ports of all the registered nodes from the service registry
def get_ports_of_nodes():
    ports_dict = {}
    response = requests.get('http://127.0.0.1:8500/v1/agent/services')
    nodes = json.loads(response.text)
    for each_service in nodes:
        service = nodes[each_service]['Service']
        status = nodes[each_service]['Port']
        key = service
        value = status
        ports_dict[key] = value
    return ports_dict

def get_higher_nodes(node_details, node_id):
    higher_node_array = []
    for each in node_details:
        if each['node_id'] > node_id:
            higher_node_array.append(each['port'])
    return higher_node_array

# this method is used to send the higher node id to the proxy
def election(higher_nodes_array, node_id):
    status_code_array = []
    for each_port in higher_nodes_array:
        url = 'http://localhost:%s/proxy' % each_port
        data = {
            "node_id": node_id
        }
        post_response = requests.post(url, json=data)
        status_code_array.append(post_response.status_code)
    if 200 in status_code_array:
        return 200


# this method is used to announce that it is the master to the other nodes.
def announce(master):
    all_nodes = get_ports_of_nodes()
    data = {
        'master': master
    }
    for each_node in all_nodes:
        url = 'http://localhost:%s/announce' % all_nodes[each_node]
        print(url)
        requests.post(url, json=data)


# this method returns if the cluster is ready for the election
def ready_for_election(ports_of_all_nodes, self_election, self_master):
    master_array = []
    election_array = []
    node_details = get_details(ports_of_all_nodes)

    for each_node in node_details:
        master_array.append(each_node['master'])
        election_array.append(each_node['election'])
    master_array.append(self_master)
    election_array.append(self_election)

    if True in election_array or True in master_array:
        return False
    else:
        return True

# this method is used to get the details of all the nodes by syncing with each node by calling each nodes' API.
def get_details(ports_of_all_nodes):
    node_details = []
    for each_node in ports_of_all_nodes:
        url = 'http://localhost:%s/nodeDetails' % ports_of_all_nodes[each_node]
        data = requests.get(url)
        print(data.content)  # add this line to print the response content
        try:
            node_details.append(data.json())
        except json.decoder.JSONDecodeError:
            print("Unable to decode response as JSON")
    return node_details

def check_health_of_the_service(service):
    print('Checking health of the %s' % service)
    url = 'http://localhost:8500/v1/agent/health/service/name/%s' % service
    response = requests.get(url)
    response_content = json.loads(response.text)
    aggregated_state = response_content[0]['AggregatedStatus']
    service_status = aggregated_state
    if response.status_code == 503 and aggregated_state == 'critical':
        service_status = 'crashed'
    print('Service status: %s' % service_status)
    return service_status


