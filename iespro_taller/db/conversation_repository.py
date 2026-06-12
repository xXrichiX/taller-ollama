"""Persistencia de conversaciones del asistente IA en MySQL."""

from db.connection import execute, fetch_all, fetch_one


class ConversationRepository:
    def crear_conversacion(
        self,
        id_usuario: int,
        id_sucursal: int,
        titulo: str | None = None,
    ) -> int:
        return execute(
            """
            INSERT INTO conversaciones (id_usuario, id_sucursal, titulo)
            VALUES (%s, %s, %s)
            """,
            (id_usuario, id_sucursal, titulo),
        )

    def obtener_conversacion_reciente(
        self,
        id_usuario: int,
        id_sucursal: int,
    ) -> dict | None:
        return fetch_one(
            """
            SELECT c.id, c.id_usuario, c.id_sucursal, c.titulo, c.creado_en, c.actualizado_en
            FROM conversaciones c
            LEFT JOIN (
                SELECT id_conversacion, MAX(id) AS ultimo_mensaje_id
                FROM mensajes_chat
                GROUP BY id_conversacion
            ) ult ON ult.id_conversacion = c.id
            WHERE c.id_usuario = %s AND c.id_sucursal = %s
            ORDER BY COALESCE(ult.ultimo_mensaje_id, 0) DESC, c.actualizado_en DESC, c.id DESC
            LIMIT 1
            """,
            (id_usuario, id_sucursal),
        )

    def actualizar_titulo(self, id_conversacion: int, titulo: str) -> None:
        execute(
            "UPDATE conversaciones SET titulo = %s WHERE id = %s",
            (titulo[:255], id_conversacion),
        )

    def guardar_mensaje(
        self,
        id_conversacion: int,
        role: str,
        contenido: str,
        route: str | None = None,
    ) -> int:
        msg_id = execute(
            """
            INSERT INTO mensajes_chat (id_conversacion, role, contenido, route)
            VALUES (%s, %s, %s, %s)
            """,
            (id_conversacion, role, contenido, route),
        )
        execute(
            "UPDATE conversaciones SET actualizado_en = CURRENT_TIMESTAMP WHERE id = %s",
            (id_conversacion,),
        )
        return msg_id

    def obtener_mensajes(self, id_conversacion: int) -> list[dict]:
        return fetch_all(
            """
            SELECT id, role, contenido, route, creado_en
            FROM mensajes_chat
            WHERE id_conversacion = %s
            ORDER BY id ASC
            """,
            (id_conversacion,),
        )

    def obtener_mensajes_para_ollama(
        self,
        id_conversacion: int,
        limite: int = 12,
    ) -> list[dict[str, str]]:
        rows = fetch_all(
            """
            SELECT role, contenido
            FROM mensajes_chat
            WHERE id_conversacion = %s
              AND role IN ('user', 'assistant')
            ORDER BY id DESC
            LIMIT %s
            """,
            (id_conversacion, limite),
        )
        rows.reverse()
        return [{"role": row["role"], "content": row["contenido"]} for row in rows]

    def listar_conversaciones(
        self,
        id_usuario: int,
        id_sucursal: int,
        limite: int = 40,
    ) -> list[dict]:
        return fetch_all(
            """
            SELECT c.id, c.titulo, c.creado_en, c.actualizado_en,
                   (SELECT COUNT(*) FROM mensajes_chat m WHERE m.id_conversacion = c.id) AS num_mensajes
            FROM conversaciones c
            LEFT JOIN (
                SELECT id_conversacion, MAX(id) AS ultimo_mensaje_id
                FROM mensajes_chat
                GROUP BY id_conversacion
            ) ult ON ult.id_conversacion = c.id
            WHERE c.id_usuario = %s AND c.id_sucursal = %s
            ORDER BY COALESCE(ult.ultimo_mensaje_id, 0) DESC, c.actualizado_en DESC, c.id DESC
            LIMIT %s
            """,
            (id_usuario, id_sucursal, limite),
        )

    def obtener_memoria_otras_conversaciones(
        self,
        id_usuario: int,
        id_sucursal: int,
        id_conversacion_actual: int,
        limite_mensajes: int = 10,
    ) -> list[dict]:
        """Fragmentos de otras charlas del mismo usuario (para contexto cruzado)."""
        return fetch_all(
            """
            SELECT c.id AS id_conversacion, c.titulo, m.role, m.contenido, m.creado_en
            FROM mensajes_chat m
            JOIN conversaciones c ON c.id = m.id_conversacion
            WHERE c.id_usuario = %s
              AND c.id_sucursal = %s
              AND c.id != %s
              AND m.role IN ('user', 'assistant')
            ORDER BY m.id DESC
            LIMIT %s
            """,
            (id_usuario, id_sucursal, id_conversacion_actual, limite_mensajes),
        )

    def listar_otras_conversaciones_con_mensajes(
        self,
        id_usuario: int,
        id_sucursal: int,
        id_conversacion_actual: int,
        limite_conversaciones: int = 5,
        limite_mensajes_por_conv: int = 8,
    ) -> list[dict]:
        """Otras charlas del usuario con sus mensajes, de más reciente a más antigua."""
        convs = fetch_all(
            """
            SELECT c.id, c.titulo
            FROM conversaciones c
            WHERE c.id_usuario = %s
              AND c.id_sucursal = %s
              AND c.id != %s
              AND EXISTS (
                  SELECT 1 FROM mensajes_chat m
                  WHERE m.id_conversacion = c.id
                    AND m.role IN ('user', 'assistant')
              )
            ORDER BY c.actualizado_en DESC, c.id DESC
            LIMIT %s
            """,
            (id_usuario, id_sucursal, id_conversacion_actual, limite_conversaciones),
        )

        resultado: list[dict] = []
        for conv in convs:
            mensajes = fetch_all(
                """
                SELECT role, contenido
                FROM (
                    SELECT role, contenido, id
                    FROM mensajes_chat
                    WHERE id_conversacion = %s
                      AND role IN ('user', 'assistant')
                    ORDER BY id DESC
                    LIMIT %s
                ) recientes
                ORDER BY id ASC
                """,
                (conv["id"], limite_mensajes_por_conv),
            )
            if mensajes:
                resultado.append({
                    "id": conv["id"],
                    "titulo": conv.get("titulo") or "Conversación",
                    "mensajes": mensajes,
                })
        return resultado
