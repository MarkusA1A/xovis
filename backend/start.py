"""
Startup-Wrapper: Patcht socket.socketpair() mit TCP-Loopback-Fallback
bevor uvicorn/asyncio geladen werden.

Proxmox blockiert den socketpair()-Syscall in Docker-Containern.
Diese Ersetzung nutzt stattdessen eine TCP-Loopback-Verbindung.
"""
import socket

_original_socketpair = socket.socketpair


def _tcp_socketpair(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0):
    """socketpair-Ersatz über TCP-Loopback (kein socketpair-Syscall nötig)."""
    try:
        return _original_socketpair(family, type, proto)
    except PermissionError:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", port))

        server, _ = listener.accept()
        listener.close()
        return server, client


socket.socketpair = _tcp_socketpair

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
