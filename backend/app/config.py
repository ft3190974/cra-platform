"""应用配置 — 通过环境变量 / .env 覆盖。"""
from pydantic_settings import BaseSettings, SettingsConfigDict

# 已知的不安全 secret 默认值（代码内占位符）。生产启动时若 secret 命中其中任一
# 且未显式放行，将拒绝启动。新增占位符时同步追加到这里。
INSECURE_DEFAULT_SECRETS = {
    "change-me-in-production-please-use-a-long-random-string",
    "please-change-to-a-long-random-secret-string",
    "change-me-in-production",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CRA_", extra="ignore")

    app_name: str = "CRA 合规平台（华南Test）"
    database_url: str = "sqlite:///./cra.db"
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 12
    upload_dir: str = "./uploads"
    cors_origins: str = "*"
    # 通知渠道
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    feishu_webhook: str = ""
    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    # 运维开关：测试/本地演示可设为 true 放行不安全 secret 与演示账号。
    # 生产环境务必保持默认 false。
    allow_insecure_secret: bool = False
    allow_demo_accounts: bool = False

    def is_secret_insecure(self) -> bool:
        """secret 为空或命中已知默认占位符即视为不安全。"""
        return self.secret_key.strip() in INSECURE_DEFAULT_SECRETS


settings = Settings()
