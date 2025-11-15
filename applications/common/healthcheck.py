from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from applications.common.mongo import get_mongo_client
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def healthcheck(request):
    """
    Health check endpoint for monitoring and deployment verification.
    Returns status of Django app and MongoDB connection.
    """
    try:
        # Check MongoDB connection
        mongo_status = 'ok'
        mongo_error = None
        try:
            client = get_mongo_client()
            # Try to ping MongoDB
            client.admin.command('ping')
        except Exception as e:
            mongo_status = 'error'
            mongo_error = str(e)
            logger.error(f"MongoDB health check failed: {e}")
        
        # Overall status
        overall_status = 'ok' if mongo_status == 'ok' else 'degraded'
        
        response_data = {
            'status': overall_status,
            'django': 'ok',
            'mongo': {
                'status': mongo_status,
                'error': mongo_error
            }
        }
        
        http_status = status.HTTP_200_OK if overall_status == 'ok' else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(response_data, status=http_status)
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

