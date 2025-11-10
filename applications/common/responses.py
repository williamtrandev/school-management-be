from rest_framework.response import Response
from rest_framework import status


def ok(data=None, message=None, status_code=status.HTTP_200_OK):
    body = {}
    if data is not None:
        body.update(data if isinstance(data, dict) else {"data": data})
    if message:
        body["message"] = message
    return Response(body or {"message": message or "OK"}, status=status_code)


def created(data=None, message="Created"):
    return ok(data=data, message=message, status_code=status.HTTP_201_CREATED)


def bad_request(error_message="Thông tin không hợp lệ", details=None):
    payload = {"error": error_message}
    if details:
        payload["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def unauthorized(error_message="Token không hợp lệ hoặc đã hết hạn"):
    return Response({"error": error_message}, status=status.HTTP_401_UNAUTHORIZED)


def forbidden(error_message="Không có quyền truy cập"):
    return Response({"error": error_message}, status=status.HTTP_403_FORBIDDEN)


def not_found(error_message="Không tìm thấy dữ liệu"):
    return Response({"error": error_message}, status=status.HTTP_404_NOT_FOUND)


def server_error(exc: Exception, fallback_message="Lỗi server"):
    return Response({"error": fallback_message, "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



