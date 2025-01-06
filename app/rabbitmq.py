import pika
import json


def send_message_to_rabbitmq(message):
    """Отправка повідомлень в RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='strategy_updates')
    channel.basic_publish(exchange='', routing_key='strategy_updates', body=message)
    connection.close()
