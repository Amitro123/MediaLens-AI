
import os
from typing import BinaryIO
from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse

def send_bytes_range_requests(
    file_obj: BinaryIO, start: int, end: int, chunk_size: int = 10_000
):
    """Yield chunks of data from file_obj between start and end."""
    with file_obj:
        file_obj.seek(start)
        while (pos := file_obj.tell()) <= end:
            read_size = min(chunk_size, end + 1 - pos)
            yield file_obj.read(read_size)


def get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse Range header and return start and end bytes."""
    try:
        if not range_header:
            return 0, file_size - 1
        
        unit, intervals = range_header.split("=", 1)
        if unit != "bytes":
            return 0, file_size - 1
            
        start_str, end_str = intervals.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        
        return start, end
    except ValueError:
        return 0, file_size - 1


def video_stream_response(file_path: str, range_header: str):
    """
    Create a StreamingResponse for video content with generic Range support.
    """
    file_size = os.path.getsize(file_path)
    start, end = get_range_header(range_header, file_size)
    
    # Ensure valid range
    if start >= file_size or end >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Requested range {start}-{end} not satisfiable",
        )
        
    chunk_size = 1024 * 1024 # 1MB chunks
    
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Type": "video/mp4",
    }
    
    return StreamingResponse(
        send_bytes_range_requests(open(file_path, "rb"), start, end, chunk_size),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
