import logging

import azure.functions as func

from shared_code.storage_proxies.service_proxy import QueueServiceProxy
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(req: func.HttpRequest) -> func.HttpResponse:

    queue_service_proxy = QueueServiceProxy()

    table_service_proxy = TableServiceProxy()

    action = req.route_params.get("action")

    resource = req.route_params.get("resource")

    name = req.route_params.get("name")

    logging.info(f':: Handling Incoming Request For {action}-{resource}-{name}')

    if resource == "queue":
        handle_queue(queue_service_proxy, action, name)

    if resource == "table":
        handle_table(table_service_proxy, action, name)

    return func.HttpResponse(f":: Completed {action} - {resource} - {name}")


def handle_queue(handler: QueueServiceProxy, action: str, name: str):
    if action == "clear":
        logging.info(f":: Performing {action} on Queue {name}")
        handler.clear_queue(name)

    if action == "create":
        logging.info(f":: Performing {action} on Queue {name}")
        handler.ensure_created()


def handle_table(handler: TableServiceProxy, action: str, name: str):

    if action == "clear":
        handler.clear_table()

    if action == "create":
        handler.ensure_created(name)



