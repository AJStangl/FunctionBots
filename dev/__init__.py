import logging
import azure.functions as func

from shared_code.models.azure_configuration import FunctionAppConfiguration


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f':: Python HTTP trigger function processed a request.')
    config = FunctionAppConfiguration()

    print(config.account_name)
    print(config.account_key)
    print(config.table_endpoint)
    print(config.queue_endpoint)
    return func.HttpResponse("ok", status_code=200)


