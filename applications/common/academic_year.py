"""
Helpers for academic year and competition period.

Academic year format: 'YYYY-YYYY', e.g. '2024-2025'.
Convention: school year starts in September and ends in May.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any

from .mongo import get_mongo_collection


ACADEMIC_YEAR_SETTINGS_KEY = "academic_year_settings"


def _parse_date(date_str: str) -> date:
  return datetime.fromisoformat(date_str).date()


def get_academic_year_from_date(date_str: str) -> str:
  """
  Tính academic year từ date string (YYYY-MM-DD)
  Quy ước: năm học bắt đầu từ tháng 9, kết thúc tháng 5 năm sau.
  """
  try:
    d = _parse_date(date_str)
  except Exception:
    d = datetime.now().date()

  year = d.year
  month = d.month

  # Nếu từ tháng 9 trở đi -> thuộc năm học mới: year-year+1
  if month >= 9:
    return f"{year}-{year + 1}"
  # Tháng 1-5 xem như thuộc năm học trước: year-1 - year
  return f"{year - 1}-{year}"


def get_current_academic_year() -> str:
  """Lấy năm học hiện tại dựa trên ngày hôm nay."""
  today = datetime.now().date()
  return get_academic_year_from_date(today.isoformat())


def get_academic_year_date_range(academic_year: str) -> Tuple[str, str]:
  """
  Trả về (start_date, end_date) cho một năm học.

  Mặc định:
    - start_date: 01/09 của năm đầu
    - end_date: 31/05 của năm sau
  """
  try:
    start_year, end_year = academic_year.split("-")
    s_y = int(start_year)
    e_y = int(end_year)
  except Exception:
    cy = datetime.now().year
    if datetime.now().month >= 9:
      s_y, e_y = cy, cy + 1
    else:
      s_y, e_y = cy - 1, cy

  start_date = date(s_y, 9, 1).isoformat()
  end_date = date(e_y, 5, 31).isoformat()
  return start_date, end_date


@dataclass
class AcademicYearConfig:
  academic_year: str
  academic_year_start: str
  academic_year_end: str
  competition_start_date: str  # mốc tuần 1 của thi đua trong năm học


def get_academic_year_settings() -> AcademicYearConfig:
  """
  Đọc cấu hình năm học hiện tại từ collection 'settings'.
  Nếu chưa có, tự tạo một cấu hình mặc định dựa trên ngày hôm nay.
  """
  settings_coll = get_mongo_collection("settings")

  doc: Optional[Dict[str, Any]] = settings_coll.find_one(
    {"key": ACADEMIC_YEAR_SETTINGS_KEY}
  )

  if not doc:
    # Tạo cấu hình mặc định
    ay = get_current_academic_year()
    ay_start, ay_end = get_academic_year_date_range(ay)

    # Mặc định competition_start_date là ngày hôm nay hoặc ay_start (tuỳ theo bạn muốn)
    today = datetime.now().date().isoformat()
    competition_start = max(today, ay_start)

    doc = {
      "key": ACADEMIC_YEAR_SETTINGS_KEY,
      "academic_year": ay,
      "academic_year_start": ay_start,
      "academic_year_end": ay_end,
      "competition_start_date": competition_start,
      "created_at": datetime.now().isoformat(),
      "updated_at": datetime.now().isoformat(),
    }
    settings_coll.insert_one(doc)

  ay = doc.get("academic_year") or get_current_academic_year()
  ay_start = doc.get("academic_year_start") or get_academic_year_date_range(ay)[0]
  ay_end = doc.get("academic_year_end") or get_academic_year_date_range(ay)[1]
  competition_start = doc.get("competition_start_date") or ay_start

  return AcademicYearConfig(
    academic_year=ay,
    academic_year_start=ay_start,
    academic_year_end=ay_end,
    competition_start_date=competition_start,
  )


def get_current_academic_year_payload() -> Dict[str, Any]:
  """
  Payload trả về cho API current academic year:
  - academic_year
  - academic_year_start
  - academic_year_end
  - competition_start_date
  """
  cfg = get_academic_year_settings()
  return {
    "academic_year": cfg.academic_year,
    "academic_year_start": cfg.academic_year_start,
    "academic_year_end": cfg.academic_year_end,
    "competition_start_date": cfg.competition_start_date,
  }


