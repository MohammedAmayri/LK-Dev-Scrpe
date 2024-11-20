import logging
import azure.functions as func
from .function_app import app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP trigger handler.
    Forwards requests to the Flask app defined in function_app.py.
    """
    try:
        with app.test_request_context(
            path=req.url,
            method=req.method,
            headers=dict(req.headers),
            data=req.get_body(),
        ):
            response = app.full_dispatch_request()
            return func.HttpResponse(
                response.get_data(as_text=True),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        logger.exception("Error in Azure Function handler.")
        return func.HttpResponse(
            "Internal server error",
            status_code=500
        )
