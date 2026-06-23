from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from loguru import logger
from app.db.database import get_db
from app.db.models import Config, User
from app.middleware.auth import get_current_user
from app.memory.session import get_session_history, append_to_history
from app.chat.prompt_builder import build_prompt
from app.chat.service import stream_ollama
from app.sessions.service import generate_session_title, persist_messages 
from app.config import get_max_context 
import json as json_lib
from app.memory.redis_client import get_redis

router = APIRouter(prefix="/chat", tags=["chat"])

class FileContext(BaseModel):
    filename: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str
    mode: str = "analysis"   # "analysis" | "edit"
    files: list[FileContext] = []

async def get_system_prompt(db: AsyncSession) -> str:
    result = await db.execute(select(Config).where(Config.key == "system_prompt"))
    config = result.scalar_one_or_none()
    return config.value if config else "Eres Huemul, un asistente de código universitario."

@router.post("/message")
async def chat_message(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"Chat message — user: {current_user.email} | "
        f"session: {body.session_id} | model: {body.model} | mode: {body.mode}"
    )

    history       = await get_session_history(body.session_id)
    system_prompt = await get_system_prompt(db)

    # ── Archivos del request + contexto guardado en Redis ──
    request_files = [{"filename": f.filename, "content": f.content} for f in body.files]

    redis = await get_redis()
    context_key = f"context:{body.session_id}"
    stored_raw  = await redis.get(context_key)
    stored_files = json_lib.loads(stored_raw) if stored_raw else []

    # Combinar: archivos del request primero, luego contexto almacenado
    all_files = request_files + [
        f for f in stored_files
        if f["filename"] not in {rf["filename"] for rf in request_files}
    ]

    max_ctx = await get_max_context(db)  

    prompt = build_prompt(
        system_prompt=system_prompt,
        history=history,
        message=body.message,
        files=all_files if all_files else None,
        mode=body.mode,
        max_context_chars=max_ctx,
    )

    await append_to_history(body.session_id, "user", body.message)

    if not history:
        await generate_session_title(body.session_id, body.message, db)

    full_response = []

    async def generate():
        async for token in stream_ollama(model=body.model, prompt=prompt):
            full_response.append(token)
            yield token
        complete = "".join(full_response)
        await append_to_history(body.session_id, "assistant", complete)
        await persist_messages(body.session_id, db)
        logger.info(
            f"Respuesta completada — session: {body.session_id} | chars: {len(complete)}"
        )

    return StreamingResponse(generate(), media_type="text/plain")
