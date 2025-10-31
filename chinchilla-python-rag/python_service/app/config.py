# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    # 공통
    env: str = "dev"

    # API Keys (.env에 지정한 대문자 키를 그대로 읽음)
    upstage_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("UPSTAGE_API_KEY", "upstage_api_key"),
    )
    serp_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("SERP_API_KEY", "serp_api_key"),
    )

    # Naver API
    naver_client_id: str = Field(
        ..., validation_alias=AliasChoices("NAVER_CLIENT_ID", "naver_client_id")
    )
    naver_client_secret: str = Field(
        ..., validation_alias=AliasChoices("NAVER_CLIENT_SECRET", "naver_client_secret")
    )

    # 선택 항목
    langsmith_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "langsmith_api_key"),
    )
    langchain_tracing_v2: bool | None = Field(
        default=True,
        validation_alias=AliasChoices("LANGCHAIN_TRACING_V2", "langchain_tracing_v2"),
    )
    langchain_project: str | None = Field(
        default="chinchilla",
        validation_alias=AliasChoices("LANGCHAIN_PROJECT", "langchain_project"),
    )

    # 기타 설정
    chroma_dir: str = Field(
        default="data/chroma_jobs",
        validation_alias=AliasChoices("CHROMA_DIR", "chroma_dir"),
    )

    jobs_data_dir: str = Field(
        default="data/raw/jobs",
        validation_alias=AliasChoices(
            "JOBS_DATA_DIR",
            "jobs_data_dir",
        ),
    )

    welfare_chroma_dir: str = Field(
        default="data/chroma_welfare",
        validation_alias=AliasChoices(
            "WELFARE_CHROMA_DIR",
            "welfare_chroma_dir",
        ),
    )

    welfare_data_dir: str = Field(
        default="data/raw/welfare",
        validation_alias=AliasChoices(
            "WELFARE_DATA_DIR",
            "welfare_data_dir",
        ),
    )

    data_raw_dir: str = Field(  # ← 누락돼 있던 필드
        default="data/raw",
        validation_alias=AliasChoices("DATA_RAW_DIR", "data_raw_dir"),
    )

    # .env 로딩 설정
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",  # 필요 시 "APP_" 같은 prefix 사용 가능
    )


# import 시 1회 생성되어 전역으로 재사용
settings = Settings()
