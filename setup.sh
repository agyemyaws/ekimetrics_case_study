#!/bin/bash

# Setup script for movie analysis automation
# Save this as setup.sh and run: chmod +x setup.sh

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install pandas numpy requests seaborn matplotlib tqdm openpyxl

# Create necessary directories
mkdir -p data output logs

# Copy the initial movies.xlsx file to data directory
cp movies.xlsx data/

# Create the crontab entry for monthly execution
(crontab -l 2>/dev/null; echo "0 0 1 * * cd $(pwd) && ./venv/bin/python movie_analysis.py >> logs/cron.log 2>&1") | crontab -

echo "Setup completed. The script will run automatically on the first day of each month."