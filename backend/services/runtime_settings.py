import base64
import hashlib
import os
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from models.app_secret import AppSecret


SECRET_CATALOG: dict[str, dict[str, Any]] = {
    "fal_key": {
        "label": "Fal.ai API Key",
        "category": "AI",
        "description": "AI 이미지 생성용 Fal.ai 키",
        "setting_attrs": [],
        "env_names": ["FAL_KEY"],
    },
    "openai_api_key": {
        "label": "OpenAI API Key",
        "category": "AI",
        "description": "GPT 엔진 호출용 OpenAI API 키",
        "setting_attrs": [],
        "env_names": ["OPENAI_API_KEY"],
    },
    "openai_base_url": {
        "label": "OpenAI Base URL",
        "category": "AI",
        "description": "OpenAI 호환 엔드포인트 기본 URL",
        "setting_attrs": [],
        "env_names": ["OPENAI_BASE_URL"],
    },
    "meta_app_id": {
        "label": "Meta App ID",
        "category": "OAuth",
        "description": "Instagram / Facebook / Threads 공용 App ID",
        "setting_attrs": ["META_APP_ID", "INSTAGRAM_APP_ID"],
        "env_names": ["META_APP_ID", "INSTAGRAM_APP_ID"],
    },
    "meta_app_secret": {
        "label": "Meta App Secret",
        "category": "OAuth",
        "description": "Instagram / Facebook / Threads 공용 App Secret",
        "setting_attrs": ["META_APP_SECRET", "INSTAGRAM_APP_SECRET"],
        "env_names": ["META_APP_SECRET", "INSTAGRAM_APP_SECRET"],
    },
    "google_client_id": {
        "label": "Google Client ID",
        "category": "OAuth",
        "description": "YouTube OAuth Client ID",
        "setting_attrs": ["GOOGLE_CLIENT_ID"],
        "env_names": ["GOOGLE_CLIENT_ID"],
    },
    "google_client_secret": {
        "label": "Google Client Secret",
        "category": "OAuth",
        "description": "YouTube OAuth Client Secret",
        "setting_attrs": ["GOOGLE_CLIENT_SECRET"],
        "env_names": ["GOOGLE_CLIENT_SECRET"],
    },
    "x_client_id": {
        "label": "X Client ID",
        "category": "OAuth",
        "description": "X(Twitter) OAuth Client ID",
        "setting_attrs": ["X_CLIENT_ID"],
        "env_names": ["X_CLIENT_ID"],
    },
    "x_client_secret": {
        "label": "X Client Secret",
        "category": "OAuth",
        "description": "X(Twitter) OAuth Client Secret",
        "setting_attrs": ["X_CLIENT_SECRET"],
        "env_names": ["X_CLIENT_SECRET"],
    },
    "naver_client_id": {
        "label": "Naver Client ID",
        "category": "OAuth",
        "description": "네이버 블로그 OAuth Client ID",
        "setting_attrs": ["NAVER_CLIENT_ID"],
        "env_names": ["NAVER_CLIENT_ID"],
    },
    "naver_client_secret": {
        "label": "Naver Client Secret",
        "category": "OAuth",
        "description": "네이버 블로그 OAuth Client Secret",
        "setting_attrs": ["NAVER_CLIENT_SECRET"],
        "env_names": ["NAVER_CLIENT_SECRET"],
    },
    "kakao_client_id": {
        "label": "Kakao Client ID",
        "category": "OAuth",
        "description": "카카오 OAuth Client ID",
        "setting_attrs": ["KAKAO_CLIENT_ID"],
        "env_names": ["KAKAO_CLIENT_ID"],
    },
    "kakao_client_secret": {
        "label": "Kakao Client Secret",
        "category": "OAuth",
        "description": "카카오 OAuth Client Secret",
        "setting_attrs": ["KAKAO_CLIENT_SECRET"],
        "env_names": ["KAKAO_CLIENT_SECRET"],
    },
    "tiktok_client_key": {
        "label": "TikTok Client Key",
        "category": "OAuth",
        "description": "TikTok OAuth Client Key",
        "setting_attrs": ["TIKTOK_CLIENT_KEY"],
        "env_names": ["TIKTOK_CLIENT_KEY"],
    },
    "tiktok_client_secret": {
        "label": "TikTok Client Secret",
        "category": "OAuth",
        "description": "TikTok OAuth Client Secret",
        "setting_attrs": ["TIKTOK_CLIENT_SECRET"],
        "env_names": ["TIKTOK_CLIENT_SECRET"],
    },
    "linkedin_client_id": {
        "label": "LinkedIn Client ID",
        "category": "OAuth",
        "description": "LinkedIn OAuth Client ID",
        "setting_attrs": ["LINKEDIN_CLIENT_ID"],
        "env_names": ["LINKEDIN_CLIENT_ID"],
    },
    "linkedin_client_secret": {
        "label": "LinkedIn Client Secret",
        "category": "OAuth",
        "description": "LinkedIn OAuth Client Secret",
        "setting_attrs": ["LINKEDIN_CLIENT_SECRET"],
        "env_names": ["LINKEDIN_CLIENT_SECRET"],
    },
    "telegram_bot_token": {
        "label": "Telegram Bot Token",
        "category": "Notifications",
        "description": "텔레그램 알림 전송용 봇 토큰",
        "setting_attrs": ["TELEGRAM_BOT_TOKEN"],
        "env_names": ["TELEGRAM_BOT_TOKEN"],
    },
    "smtp_host": {
        "label": "SMTP Host",
        "category": "Notifications",
        "description": "메일 발송 서버 주소",
        "setting_attrs": ["SMTP_HOST"],
        "env_names": ["SMTP_HOST"],
    },
    "smtp_port": {
        "label": "SMTP Port",
        "category": "Notifications",
        "description": "메일 발송 서버 포트",
        "setting_attrs": ["SMTP_PORT"],
        "env_names": ["SMTP_PORT"],
    },
    "smtp_user": {
        "label": "SMTP User",
        "category": "Notifications",
        "description": "메일 발송 계정",
        "setting_attrs": ["SMTP_USER"],
        "env_names": ["SMTP_USER"],
    },
    "smtp_password": {
        "label": "SMTP Password",
        "category": "Notifications",
        "description": "메일 발송 비밀번호",
        "setting_attrs": ["SMTP_PASSWORD"],
        "env_names": ["SMTP_PASSWORD"],
    },
    "smtp_from_email": {
        "label": "SMTP From Email",
        "category": "Notifications",
        "description": "발신 이메일 주소",
        "setting_attrs": ["SMTP_FROM_EMAIL"],
        "env_names": ["SMTP_FROM_EMAIL"],
    },
    "smtp_from_name": {
        "label": "SMTP From Name",
        "category": "Notifications",
        "description": "발신자 이름",
        "setting_attrs": ["SMTP_FROM_NAME"],
        "env_names": ["SMTP_FROM_NAME"],
    },
}


def _master_fernet() -> Fernet:
    seed = settings.JWT_SECRET or "aimtop-sns-secret-default"
    digest = hashlib.sha256(seed.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_app_secret(value: str) -> str:
    return _master_fernet().encrypt(value.encode()).decode()


def decrypt_app_secret(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _master_fernet().decrypt(value.encode()).decode()
    except Exception:
        return ""


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}••••{value[-4:]}"


async def _fetch_secret_record(secret_key: str, db: AsyncSession) -> AppSecret | None:
    result = await db.execute(select(AppSecret).where(AppSecret.secret_key == secret_key))
    return result.scalar_one_or_none()


async def list_secret_settings(db: AsyncSession) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for secret_key, meta in SECRET_CATALOG.items():
        record = await _fetch_secret_record(secret_key, db)
        db_value = decrypt_app_secret(record.encrypted_value) if record and record.is_active else ""
        attr_value = next((str(getattr(settings, name, "") or "") for name in meta.get("setting_attrs", []) if getattr(settings, name, "")), "")
        env_value = attr_value or next((os.getenv(name, "") for name in meta["env_names"] if os.getenv(name, "")), "")
        effective = db_value or env_value
        source = "db" if db_value else ("env" if env_value else "empty")
        items.append({
            "id": str(record.id) if record else None,
            "secret_key": secret_key,
            "label": meta["label"],
            "category": meta["category"],
            "description": meta.get("description"),
            "configured": bool(effective),
            "source": source,
            "masked_value": mask_secret(effective),
            "is_active": record.is_active if record else True,
            "updated_at": record.updated_at if record else None,
        })
    return items


async def upsert_secret_setting(db: AsyncSession, secret_key: str, value: str | None, is_active: bool, updated_by=None) -> AppSecret:
    if secret_key not in SECRET_CATALOG:
        raise ValueError(f"지원하지 않는 시크릿 키: {secret_key}")
    record = await _fetch_secret_record(secret_key, db)
    encrypted_value = encrypt_app_secret(value.strip()) if value and value.strip() else None
    if record:
        if encrypted_value is not None:
            record.encrypted_value = encrypted_value
        record.is_active = is_active
        record.updated_by = updated_by
        record.description = SECRET_CATALOG[secret_key].get("description")
    else:
        record = AppSecret(
            secret_key=secret_key,
            encrypted_value=encrypted_value,
            is_active=is_active,
            updated_by=updated_by,
            description=SECRET_CATALOG[secret_key].get("description"),
        )
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_runtime_setting(secret_key: str, db: AsyncSession | None = None) -> str:
    if secret_key not in SECRET_CATALOG:
        return ""

    async def _resolve(session: AsyncSession) -> str:
        record = await _fetch_secret_record(secret_key, session)
        if record and record.is_active:
            value = decrypt_app_secret(record.encrypted_value)
            if value:
                return value
        for attr_name in SECRET_CATALOG[secret_key].get("setting_attrs", []):
            attr_value = getattr(settings, attr_name, "")
            if attr_value:
                return str(attr_value)
        for env_name in SECRET_CATALOG[secret_key]["env_names"]:
            env_value = os.getenv(env_name, "")
            if env_value:
                return env_value
        return ""

    if db is not None:
        return await _resolve(db)

    async with AsyncSessionLocal() as session:
        return await _resolve(session)
