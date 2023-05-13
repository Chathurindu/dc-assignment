import pika

class RabbitMQSidecar:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue = 'logs'

    def connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue)

    def send_message(self, message):
        self.channel.basic_publish(exchange='', routing_key=self.queue, body=message)

    def disconnect(self):
        self.connection.close()
