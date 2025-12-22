
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock, MagicMock

client = TestClient(app)

@patch("app.api.routes.NativeDriveClient")
def test_list_drive_files(mock_client_cls):
    """Test listing files via Native Client"""
    # Mock the client instance and list_files method
    mock_instance = mock_client_cls.return_value
    mock_instance.list_files = AsyncMock(return_value=[
        {"id": "drive://123", "name": "test_video.mp4", "mimeType": "video/mp4"}
    ])
    
    response = client.get("/api/v1/integrations/drive/files")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "test_video.mp4"

@patch("app.api.routes.NativeDriveClient")
@patch("app.api.routes.process_video_pipeline", new_callable=AsyncMock)
@patch("app.services.storage_service.StorageService.add_session")
def test_import_drive_file(mock_add_session, mock_pipeline, mock_client_cls):
    """Test importing a file triggers pipeline"""
    # Mock download
    mock_instance = mock_client_cls.return_value
    mock_instance.download_file = AsyncMock(return_value=True)
    
    # Mock pipeline return
    mock_pipeline.return_value = MagicMock(documentation="# Docs")
    
    payload = {
        "file_uri": "drive://123",
        "file_name": "Imported Video.mp4",
        "mode": "bug_report"
    }
    
    response = client.post("/api/v1/import/drive", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    
    # Verify mock calls
    mock_instance.download_file.assert_called_once()
    mock_pipeline.assert_called_once()
    mock_add_session.assert_called_once()
