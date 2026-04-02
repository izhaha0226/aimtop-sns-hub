"""
Reports Routes - 월간 리포트, PDF, CSV 내보내기 API.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.report_service import ReportService
from middleware.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/monthly/{year}/{month}")
async def get_monthly_report(
    year: int,
    month: int,
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """월간 리포트 데이터 조회."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="월은 1~12 범위여야 합니다")
    if not (2020 <= year <= 2100):
        raise HTTPException(status_code=400, detail="연도 범위가 올바르지 않습니다")

    svc = ReportService(db)
    report = await svc.generate_monthly_report(client_id, year, month)
    return {"ok": True, "data": report}


@router.get("/monthly/{year}/{month}/pdf")
async def download_monthly_pdf(
    year: int,
    month: int,
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """월간 리포트 PDF 다운로드."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="월은 1~12 범위여야 합니다")

    svc = ReportService(db)
    report = await svc.generate_monthly_report(client_id, year, month)
    filepath = await svc.generate_pdf(report)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="리포트 파일 생성 실패")

    filename = os.path.basename(filepath)
    media_type = "application/pdf" if filepath.endswith(".pdf") else "text/html"
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
    )


@router.get("/export/csv")
async def export_csv(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    start_date: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """CSV 내보내기."""
    svc = ReportService(db)
    try:
        filepath = await svc.export_csv(client_id, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="CSV 파일 생성 실패")

    return FileResponse(
        path=filepath,
        filename=os.path.basename(filepath),
        media_type="text/csv",
    )
