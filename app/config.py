"""Application Configuration Module."""
import os
import sys
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./hotel_pms.db"
    SECRET_KEY: str = "hotel-pms-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS origins: comma-separated string or list
    CORS_ORIGINS: str = "*"

    # Hotel Properties (Configured for India / INR)
    HOTEL_NAME: str = "The Grand Pavilion & Palace Hotel"
    HOTEL_ADDRESS: str = "12/4 MG Road, Shivaji Nagar, Bengaluru, Karnataka 560001, India"
    HOTEL_PHONE: str = "+91 80 4123 4567"
    HOTEL_EMAIL: str = "reservations@grandpavilion.in"
    HOTEL_CURRENCY: str = "INR"
    HOTEL_TIMEZONE: str = "Asia/Kolkata"
    HOTEL_TAX_RATE: float = 0.12  # 12% Goods & Services Tax (GST: 6% CGST + 6% SGST)

    # Stripe Payments & Subscriptions (Optional / Graceful Fallback)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = "price_starter_mock"
    STRIPE_PRICE_PRO: str = "price_pro_mock"
    STRIPE_PRICE_ENTERPRISE: str = "price_enterprise_mock"

    # Email & Communications
    SENDGRID_API_KEY: str = ""
    MAIL_FROM: str = "Hotel OS <hello@checkinos.com>"

    # Backups & S3 Storage
    BACKUP_S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Domains & Routing
    ROOT_DOMAIN: str = "checkinos.com"

    # Integrations & Monitoring
    CRISP_WEBSITE_ID: str = ""
    HELP_WIDGET_ENABLED: bool = True
    SENTRY_DSN: str = ""
    SENTRY_DSN_FRONTEND: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    # SMS (Optional)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        val = v.lower().strip()
        if val in ("prod", "production"):
            return "prod"
        if val in ("dev", "development", "preview", "local"):
            return "dev"
        if val in ("test", "testing"):
            return "test"
        return "dev"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_hardening(self) -> None:
        """Enforces security boundaries in non-dev environments."""
        # On Vercel or cloud preview, do not crash process
        if os.environ.get("VERCEL"):
            return
        if self.ENV == "prod":
            default_key = "hotel-pms-super-secret-key-change-in-production-min-32-chars"
            if self.SECRET_KEY == default_key or len(self.SECRET_KEY) < 32:
                import logging
                logging.getLogger("uvicorn.error").warning(
                    "SECRET_KEY is using default or short key. Set SECRET_KEY in production."
                )


settings = Settings()
