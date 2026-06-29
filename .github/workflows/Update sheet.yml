name: Update WoW Midcap Smallcap to Google Sheet

on:
  schedule:
    # Chạy 8:00 sáng giờ Việt Nam (UTC+7) mỗi ngày từ thứ 2-6
    # GitHub Actions dùng giờ UTC nên 8:00 VN = 1:00 UTC
    - cron: '0 1 * * 1-6'
  workflow_dispatch:  # cho phép bấm nút "Run workflow" để chạy tay trên GitHub

jobs:
  update-sheet:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run script
        env:
          GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}
          SHEET_ID: ${{ secrets.SHEET_ID }}
        run: python wow_to_gsheet.py
