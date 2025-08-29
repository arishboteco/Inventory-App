import logging
import traceback

logger = logging.getLogger(__name__)

class DetailedErrorLoggingMiddleware:
    """
    Middleware to log detailed error information for debugging
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Log detailed exception information
        """
        logger.error('🚨 DETAILED ERROR REPORT 🚨')
        logger.error(f'Exception Type: {type(exception).__name__}')
        logger.error(f'Exception Message: {str(exception)}')
        logger.error(f'Request Path: {request.path}')
        logger.error(f'Request Method: {request.method}')
        logger.error(f'Request User: {getattr(request, "user", "Anonymous")}')
        logger.error(f'Request META: {dict(request.META)}')

        if request.method == 'POST':
            logger.error(f'POST Data: {dict(request.POST)}')

        logger.error('🔍 FULL TRACEBACK:')
        logger.error(traceback.format_exc())
        logger.error('🚨 END ERROR REPORT 🚨')

        # Don't return a response - let Django handle it normally
        return None
