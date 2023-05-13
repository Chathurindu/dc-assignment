from flask import Flask, request
import math
import requests
import consul
import uuid

app = Flask(__name__)

port = int(input("Enter port number: "))
assert port

service_name = input("Enter node name: ")
assert service_name

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

if __name__ == '__main__':
    # Register with Consul
    consul_client = consul.Consul()
    service_port = port
    service_id = generate_service_id_id()
    consul_client.agent.service.register(
        name=service_name,
        service_id=str(service_id),
        address='localhost',
        port=service_port,
        check=consul.Check.tcp('localhost', service_port, interval='10s')
    )
    # Start Flask app
    app.run(host='127.0.0.1', port=port)
