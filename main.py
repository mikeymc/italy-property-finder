# ABOUTME: Entry point that starts the Flask API server.
# ABOUTME: Loads OMI data from SQLite and serves the zone exploration + analysis API.

import os
from src.api import create_app

DB_PATH = os.environ.get("DB_PATH", "data/real_estate.db")


def main():
    app = create_app(DB_PATH)
    app.run(debug=True, port=5001)


if __name__ == "__main__":
    main()
