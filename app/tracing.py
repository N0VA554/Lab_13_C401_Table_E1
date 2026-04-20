# tracing.py
import os
from langfuse import observe, get_client

def tracing_enabled() -> bool:
    # Kiểm tra xem các biến môi trường cần thiết đã được cài đặt chưa
    return all([
        os.getenv("LANGFUSE_PUBLIC_KEY"),
        os.getenv("LANGFUSE_SECRET_KEY"),
        os.getenv("LANGFUSE_HOST")
    ])

def get_langfuse_client():
    """Get the Langfuse client singleton for updating traces/spans."""
    return get_client()

# Xuất bản các decorators để dùng ở agent.py
__all__ = ["observe", "get_langfuse_client", "tracing_enabled"]