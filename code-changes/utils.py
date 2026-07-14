from bacnet_mcp.settings import Settings


def get_device(
    settings: Settings,
    name: str | None = None,
    host: str | None = None,
    port: str | int | None = None,
) -> tuple[str, int]:
    """Find a device by name or return the default settings."""
    if name:
        for x in settings.devices:
            if x.name == name:
                return x.host, x.port
        raise RuntimeError("Device not found")

    if isinstance(port, str):
        port = port.strip()
        if port == "":
            port = None
        else:
            port = int(port)

    return (
        host if host is not None else settings.bacnet.host,
        port if port is not None else settings.bacnet.port,
    )
