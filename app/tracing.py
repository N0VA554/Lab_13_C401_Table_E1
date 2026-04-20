# tracing.py
import os
from langfuse.decorators import observe, langfuse_context

def tracing_enabled() -> bool:
    # Kiểm tra xem các biến môi trường cần thiết đã được cài đặt chưa
    return all([
        os.getenv("LANGFUSE_PUBLIC_KEY"),
        os.getenv("LANGFUSE_SECRET_KEY"),
        os.getenv("LANGFUSE_HOST")
    ])

# Xuất bản các decorators để dùng ở agent.py
__all__ = ["observe", "langfuse_context", "tracing_enabled"]