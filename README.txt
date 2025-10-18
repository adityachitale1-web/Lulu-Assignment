Lulu UAE Streamlit Dashboard
Files:
- app.py : Streamlit app (single-file)
- lulu_uae_master_2000.csv : source data (must be in same folder)

To run locally:
1. pip install streamlit pandas matplotlib
2. cd /mnt/data/streamlit_app
3. streamlit run app.py

To push to GitHub:
- git init
- git add app.py lulu_uae_master_2000.csv
- git commit -m "Add Lulu UAE pricing & discount dashboard"
- create a repo on GitHub and push.

To deploy on Streamlit Cloud:
- Push the repository to GitHub, then connect the repo on share.streamlit.io and deploy.

