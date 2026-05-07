from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_speech_service
from app.api.schemas import ErrorResponse, SpeechTranscriptionResponse
from app.application.speech_service import SpeechService
from app.domain.errors import (
    SpeechConcurrencyLimitError,
    SpeechToTextConfigurationError,
    SpeechTranscriptionError,
    SpeechUploadTooLargeError,
    UnsupportedAudioTypeError,
)
from app.identity.dependencies import require_current_user
from app.identity.service import CurrentSession

router = APIRouter(prefix="/api/speech", tags=["speech"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


@router.post(
    "/transcribe",
    response_model=SpeechTranscriptionResponse,
    responses=ERROR_RESPONSES,
)
async def transcribe_speech(
    audio: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    speech_service: SpeechService = Depends(get_speech_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SpeechTranscriptionResponse:
    """Transcribe one authenticated audio upload without creating a training turn."""
    del current_session
    try:
        payload = await speech_service.transcribe_upload(upload=audio, session_id=session_id)
    except SpeechUploadTooLargeError as error:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(error)) from error
    except UnsupportedAudioTypeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except SpeechConcurrencyLimitError as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)) from error
    except SpeechToTextConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SpeechTranscriptionError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return SpeechTranscriptionResponse.model_validate(payload)
