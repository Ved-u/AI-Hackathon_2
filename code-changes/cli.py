import asyncio
import typer

from bacnet_mcp.server import BACnetMCP


app = typer.Typer(
    name="bacnet-mcp",
    help="BACnetMCP CLI",
)


@app.command()
def run(
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
    address: str | None = typer.Option(
        None,
        "--address",
        help="Local BACnet/IP address (example: 10.183.155.34/24)",
    ),
):
    kwargs: dict[str, object] = {}

    if host is not None:
        kwargs["host"] = host

    if port is not None:
        kwargs["port"] = port

    if address is not None:
        kwargs["address"] = address

    server = BACnetMCP(address=address)

    server = BACnetMCP(address=address)

    asyncio.run(
        server.run_async(
            transport="http",
            host=host,
            port=port,
        )
    )
