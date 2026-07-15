import streamlit as st


st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGES = [
    ("Home", "pages/01_home.py"),
    ("Company Profile", "pages/02_profile.py"),
    ("Screener", "pages/03_screener.py"),
    ("Peers", "pages/04_peers.py"),
    ("Trends", "pages/05_trends.py"),
    ("Sectors", "pages/06_sectors.py"),
    ("Capital Allocation", "pages/07_capital.py"),
    ("Reports", "pages/08_reports.py"),
]


def main():
    st.title("Nifty 100 Analytics")
    st.write("Sprint 4 dashboard scaffold for the Financial Intelligence Platform.")

    st.sidebar.title("Navigation")
    for label, page_path in PAGES:
        st.sidebar.page_link(page_path, label=label)


if __name__ == "__main__":
    main()
