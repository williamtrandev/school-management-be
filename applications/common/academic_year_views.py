from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .academic_year import get_current_academic_year_payload


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_academic_year(request):
  """
  API trả về thông tin niên khoá & mốc thi đua hiện tại.

  Response:
    {
      "academic_year": "2024-2025",
      "academic_year_start": "2024-09-01",
      "academic_year_end": "2025-05-31",
      "competition_start_date": "2024-10-06"
    }
  """
  payload = get_current_academic_year_payload()
  return Response(payload)


