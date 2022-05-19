import logging
import os
import azure.functions as func


from shared_code.storage_proxies.service_proxy import QueueServiceProxy

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f':: Python HTTP trigger function processed a request.')


    proxy = QueueServiceProxy()
    logging.info(":: Preparing Queues")
    proxy.ensure_created()

    foo = os.environ(["Bots"])
    print(foo)
    