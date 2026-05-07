from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.access.service import AccessService
from app.api.dependencies import get_speech_service
from app.api.schemas import ErrorResponse, SpeechTranscriptionResponse
from app.application.speech_service import SpeechService
from app.domain.errors import (
    SpeechConcurrencyLimitError,
    SpeechDisabledError,
    SpeechDurationUnknownError,
    SpeechQueueTimeoutError,
    SpeechToTextConfigurationError,
    SpeechTranscriptionError,
    SpeechUploadTooLargeError,
    UnsupportedAudioTypeError,
)
from app.identity.dependencies import get_access_service, require_current_user
from app.identity.service import CurrentSession


ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


def build_speech_router() -> APIRouter:
    """Build the speech router lazily so multipart dependency is only required when enabled."""
    router = APIRouter(prefix="/api/speech", tags=["speech"])

    @router.post(
        "/transcribe",
        response_model=SpeechTranscriptionResponse,
        responses=ERROR_RESPONSES,
    )
    async def transcribe_speech(
        audio: UploadFile = File(...),
        session_id: str | None = Form(default=None),
        speech_service: SpeechService = Depends(get_speech_service),
        access_service: AccessService = Depends(get_access_service),
        current_session: CurrentSession = Depends(require_current_user),
    ) -> SpeechTranscriptionResponse:
        """Transcribe one authenticated audio upload without creating a training turn."""
        try:
            if session_id is not None:
                access_service.require_session_access(session_id, current_session.user.id)
            payload = await speech_service.transcribe_upload(
                upload=audio,
                session_id=session_id,
                user_id=str(current_session.user.id),
            )
        except SpeechUploadTooLargeError as error:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(error)) from error
        except UnsupportedAudioTypeError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
        except SpeechConcurrencyLimitError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        except SpeechQueueTimeoutError as error:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)) from error
        except SpeechDisabledError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        except SpeechDurationUnknownError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
        except SpeechToTextConfigurationError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        except SpeechTranscriptionError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        return SpeechTranscriptionResponse.model_validate(payload)

    return router
