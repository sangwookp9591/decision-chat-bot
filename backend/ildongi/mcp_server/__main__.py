"""make mcp / python -m ildongi.mcp_server entrypoint."""

from ildongi.mcp_server.api import create_server


def main():
    server = create_server()
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
