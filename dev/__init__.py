import logging
import os
import azure.functions as func
import sys




def main(req: func.HttpRequest) -> func.HttpResponse:
    from shared_code.storage_proxies.service_proxy import QueueServiceProxy
    logging.info(f':: Python HTTP trigger function processed a request.')


    proxy = QueueServiceProxy()
    logging.info(":: Preparing Queues")
    proxy.ensure_created()

    
    
    