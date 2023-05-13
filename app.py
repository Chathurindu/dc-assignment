import logging
import threading

from flask import Flask, request, jsonify

from node import Node
from run import initiate_node
from utils import register_service, generate_node_id, get_node_details_util, response_node_util,\
    announce_master_util, proxy_util, proposers_util, prime_result_util, prime_result_util,proposer_schedule_util, \
    final_result_util
from rabbitmq_sidecar import RabbitMQSidecar

app = Flask(__name__)

# getting port number and node name from command line arguments
port = int(input("Enter port number: "))
assert port

node_name = input("Enter node name: ")
assert node_name

# Connect to RabbitMQ
rabbitmq_sidecar = RabbitMQSidecar()
rabbitmq_sidecar.connect()

# # saving the API logs to a file
# logging.basicConfig(filename=f"logs/{node_name}.log", level=logging.INFO)

node_id = generate_node_id()
node = Node(node_id, node_name, port)
# register service in the Service Registry
service_register_status = register_service(node_name, port, node_id)
rabbitmq_sidecar.send_message(f"Service register status: {service_register_status}")

# this api is used to exchange details with each node
@app.route('/nodeDetails', methods=['GET'])
def get_node_details():
    get_node_details_util(node)


@app.route('/response', methods=['POST'])
def response_node():
    data = request.get_json()
    response_node_util(data, node)


# This API is used to announce the master details.
@app.route('/announce', methods=['POST'])
def announce_master():
    data = request.get_json()
    announce_master_util(data, node)


@app.route('/proxy', methods=['POST'])
def proxy():
    data = request.get_json()
    proxy_util(data, node)


@app.route('/acceptor', methods=['POST'])
def acceptors():
    data = request.get_json()
    print(data)
    return jsonify({'response': 'OK'}), 200


@app.route('/learner', methods=['POST'])
def learners():
    data = request.get_json()
    print(data)
    return jsonify({'response': 'OK'}), 200


@app.route('/proposer', methods=['POST'])
def proposers():
    data = request.get_json()
    proposers_util(data, node)


@app.route('/primeResult', methods=['POST'])
def prime_result():
    data = request.get_json()
    prime_result_util(data)


@app.route('/proposer-schedule', methods=['POST'])
def proposer_schedule():
    data = request.get_json()
    proposer_schedule_util(data)


@app.route('/finalResult', methods=['POST'])
def final_result():
    data = request.get_json()
    final_result_util(data)

timer_thread1 = threading.Timer(15, initiate_node, args=(service_register_status, node))
timer_thread1.start()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=port)
