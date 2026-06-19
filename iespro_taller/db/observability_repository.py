"""Persistencia de métricas de observabilidad del agente (Semana 5)."""

from __future__ import annotations

import json
from typing import Any

from db.connection import execute, fetch_all


class ObservabilityRepository:
    def ensure_table(self) -> None:
        execute(
            """
            CREATE TABLE IF NOT EXISTS llm_observability_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(120) NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_prompt TEXT NOT NULL,
                system_response LONGTEXT,
                ttft_ms INT NULL,
                total_latency_ms INT NOT NULL,
                tokens_per_second DECIMAL(10,2) NULL,
                was_blocked TINYINT(1) NOT NULL DEFAULT 0,
                tools_executed JSON NULL,
                INDEX idx_obs_session (session_id),
                INDEX idx_obs_timestamp (timestamp)
            )
            """
        )

    def insert_log(
        self,
        *,
        session_id: str,
        user_prompt: str,
        system_response: str,
        ttft_ms: int | None,
        total_latency_ms: int,
        tokens_per_second: float | None,
        was_blocked: bool,
        tools_executed: list[dict[str, Any]],
    ) -> int:
        return execute(
            """
            INSERT INTO llm_observability_logs (
                session_id, user_prompt, system_response, ttft_ms, total_latency_ms,
                tokens_per_second, was_blocked, tools_executed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                user_prompt,
                system_response,
                ttft_ms,
                total_latency_ms,
                tokens_per_second,
                1 if was_blocked else 0,
                json.dumps(tools_executed, ensure_ascii=False),
            ),
        )

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return fetch_all(
            """
            SELECT id, session_id, timestamp, user_prompt, system_response,
                   ttft_ms, total_latency_ms, tokens_per_second, was_blocked, tools_executed
            FROM llm_observability_logs
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
