\
import sys, os
from streamlit.web.cli import main as stcli

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    app = os.path.join(here, "app.py")
    # headless=true vermeidet eine zweite Konsole im EXE-Modus
    sys.argv = ["streamlit", "run", app, "--server.headless=true"]
    sys.exit(stcli())
