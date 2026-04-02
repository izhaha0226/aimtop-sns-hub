"""
Report Service - 월간 리포트, PDF, CSV 내보내기.
"""
import csv
import io
import os
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.content import Content
from models.analytics import Analytics
from services.ai_service import call_claude

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_monthly_report(
        self, client_id: uuid.UUID, year: int, month: int
    ) -> dict:
        """월간 리포트 데이터 집계."""
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # 콘텐츠 수 집계
        content_result = await self.db.execute(
            select(func.count(Content.id)).where(
                and_(
                    Content.client_id == client_id,
                    Content.created_at >= start_date,
                    Content.created_at < end_date,
                )
            )
        )
        total_contents = content_result.scalar() or 0

        # 상태별 집계
        status_result = await self.db.execute(
            select(Content.status, func.count(Content.id)).where(
                and_(
                    Content.client_id == client_id,
                    Content.created_at >= start_date,
                    Content.created_at < end_date,
                )
            ).group_by(Content.status)
        )
        status_breakdown = {row[0]: row[1] for row in status_result.all()}

        # Analytics 집계
        analytics_result = await self.db.execute(
            select(
                func.sum(Analytics.impressions),
                func.sum(Analytics.reach),
                func.sum(Analytics.likes),
                func.sum(Analytics.comments),
                func.sum(Analytics.shares),
                func.sum(Analytics.clicks),
            ).where(
                and_(
                    Analytics.client_id == client_id,
                    Analytics.date >= start_date.date(),
                    Analytics.date < end_date.date(),
                )
            )
        )
        stats = analytics_result.one()
        impressions = stats[0] or 0
        reach = stats[1] or 0
        likes = stats[2] or 0
        comments = stats[3] or 0
        shares = stats[4] or 0
        clicks = stats[5] or 0

        engagement_total = likes + comments + shares
        engagement_rate = round(engagement_total / reach * 100, 2) if reach > 0 else 0.0

        # 상위 콘텐츠
        top_contents_result = await self.db.execute(
            select(Content.id, Content.title, Content.platform, Content.status)
            .where(
                and_(
                    Content.client_id == client_id,
                    Content.created_at >= start_date,
                    Content.created_at < end_date,
                )
            )
            .order_by(Content.created_at.desc())
            .limit(10)
        )
        top_contents = [
            {
                "id": str(row[0]),
                "title": row[1],
                "platform": row[2],
                "status": row[3],
            }
            for row in top_contents_result.all()
        ]

        # AI 추천
        ai_recommendations = []
        try:
            summary_text = (
                f"월간 실적: 콘텐츠 {total_contents}건, 도달 {reach}, "
                f"참여율 {engagement_rate}%, 좋아요 {likes}, 댓글 {comments}"
            )
            prompt = (
                f"다음 SNS 월간 실적을 분석하고 개선 추천사항 3가지를 JSON 배열로 제공해줘.\n"
                f"실적: {summary_text}\n\n"
                f'[{{"recommendation": "...", "priority": "high/medium/low"}}] 형식으로 응답.'
            )
            raw = await call_claude(prompt)
            from services.ai_service import _parse_json_response
            ai_recommendations = _parse_json_response(raw)
            if not isinstance(ai_recommendations, list):
                ai_recommendations = [ai_recommendations]
        except Exception as e:
            logger.warning("AI recommendation failed: %s", e)
            ai_recommendations = [{"recommendation": "AI 분석 일시 불가", "priority": "low"}]

        report = {
            "client_id": str(client_id),
            "year": year,
            "month": month,
            "summary": {
                "total_contents": total_contents,
                "status_breakdown": status_breakdown,
                "impressions": impressions,
                "reach": reach,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "clicks": clicks,
                "engagement_rate": engagement_rate,
            },
            "top_contents": top_contents,
            "growth": {
                "engagement_rate": engagement_rate,
                "total_engagement": engagement_total,
            },
            "ai_recommendations": ai_recommendations,
        }
        return report

    async def generate_pdf(self, report_data: dict) -> str:
        """WeasyPrint로 PDF 생성, 파일 경로 반환."""
        year = report_data["year"]
        month = report_data["month"]
        client_id = report_data["client_id"]
        summary = report_data["summary"]
        recommendations = report_data.get("ai_recommendations", [])

        rec_html = ""
        for r in recommendations:
            rec_text = r.get("recommendation", "") if isinstance(r, dict) else str(r)
            priority = r.get("priority", "") if isinstance(r, dict) else ""
            rec_html += f"<li><strong>[{priority}]</strong> {rec_text}</li>"

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; padding: 30px; color: #333; }}
  h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
  .metric {{ display: inline-block; width: 140px; margin: 10px; padding: 15px;
             background: #f5f5f5; border-radius: 8px; text-align: center; }}
  .metric .value {{ font-size: 24px; font-weight: bold; color: #1a73e8; }}
  .metric .label {{ font-size: 12px; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #1a73e8; color: white; }}
</style></head><body>
<h1>{year}년 {month}월 월간 리포트</h1>
<p>클라이언트 ID: {client_id}</p>

<h2>주요 지표</h2>
<div class="metric"><div class="value">{summary['total_contents']}</div><div class="label">총 콘텐츠</div></div>
<div class="metric"><div class="value">{summary['reach']:,}</div><div class="label">도달</div></div>
<div class="metric"><div class="value">{summary['impressions']:,}</div><div class="label">노출</div></div>
<div class="metric"><div class="value">{summary['engagement_rate']}%</div><div class="label">참여율</div></div>
<div class="metric"><div class="value">{summary['likes']:,}</div><div class="label">좋아요</div></div>
<div class="metric"><div class="value">{summary['comments']:,}</div><div class="label">댓글</div></div>

<h2>AI 추천사항</h2>
<ul>{rec_html if rec_html else '<li>추천 데이터 없음</li>'}</ul>

<p style="margin-top:40px;color:#999;font-size:11px;">
  Generated by AimTop SNS Hub &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')}
</p>
</body></html>"""

        filename = f"report_{client_id}_{year}_{month:02d}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(filepath)
        except ImportError:
            # WeasyPrint 미설치 시 HTML 파일로 대체
            html_path = filepath.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.warning("WeasyPrint not installed, saved HTML instead: %s", html_path)
            return html_path

        logger.info("PDF generated: %s", filepath)
        return filepath

    async def export_csv(
        self,
        client_id: uuid.UUID,
        start_date: str,
        end_date: str,
    ) -> str:
        """CSV 내보내기."""
        from datetime import date as date_type

        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()

        # 콘텐츠 조회
        result = await self.db.execute(
            select(
                Content.id,
                Content.title,
                Content.platform,
                Content.status,
                Content.post_type,
                Content.created_at,
            ).where(
                and_(
                    Content.client_id == client_id,
                    Content.created_at >= datetime.combine(sd, datetime.min.time()).replace(tzinfo=timezone.utc),
                    Content.created_at < datetime.combine(ed, datetime.min.time()).replace(tzinfo=timezone.utc),
                )
            ).order_by(Content.created_at.desc())
        )
        rows = result.all()

        filename = f"export_{client_id}_{start_date}_{end_date}.csv"
        filepath = os.path.join(REPORTS_DIR, filename)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "제목", "플랫폼", "상태", "유형", "생성일"])
            for row in rows:
                writer.writerow([
                    str(row[0]),
                    row[1] or "",
                    row[2] or "",
                    row[3] or "",
                    row[4] or "",
                    row[5].isoformat() if row[5] else "",
                ])

        logger.info("CSV exported: %s (%d rows)", filepath, len(rows))
        return filepath
