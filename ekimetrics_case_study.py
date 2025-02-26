#!/usr/bin/env python3
"""
Neon Films Movie Analysis Script
Author: [Your Name]
Date: February 2025

This script analyzes movie data using OMDB API to help
Neon Films make data-driven decisions about movie production.
"""

import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from tqdm import tqdm
import logging
from pathlib import Path
import json
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_analysis.log'),
        logging.StreamHandler()
    ]
)

class MovieAnalyzer:
    """Main class for movie data analysis and automation."""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the MovieAnalyzer with configuration."""
        self.config = self._load_config(config_path)
        self.omdb_api_key = self.config['api_keys']['omdb']
        self.data_dir = Path(self.config['paths']['data_directory'])
        self.output_dir = Path(self.config['paths']['output_directory'])
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default config if not exists
            default_config = {
                "api_keys": {
                    "omdb": "f710ddc8"
                },
                "paths": {
                    "data_directory": "data",
                    "output_directory": "output"
                },
                "analysis": {
                    "min_year": 2006,
                    "min_box_office": 0
                }
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def fetch_omdb_data(self, title: str) -> dict:
        """Fetch movie details from OMDB API with error handling."""
        params = {
            'apikey': self.omdb_api_key,
            't': title,
            'type': 'movie'
        }
        try:
            response = requests.get('http://www.omdbapi.com/', params=params)
            if response.status_code == 200:
                data = response.json()
                return data if data.get('Response') == 'True' else {}
            else:
                logging.error(f"OMDB API error for {title}: {response.status_code}")
                return {}
        except Exception as e:
            logging.error(f"Error fetching OMDB data for {title}: {str(e)}")
            return {}

    def update_movie_data(self) -> pd.DataFrame:
        """Update movie data with OMDB information."""
        try:
            df_movies = pd.read_excel(self.data_dir / 'movies.xlsx')
            logging.info(f"Loaded {len(df_movies)} movies from source file")
            
            updated_movies = []
            for _, row in tqdm(df_movies.iterrows(), total=len(df_movies)):
                movie_data = self._process_single_movie(row['title'])
                if movie_data:
                    updated_movies.append(movie_data)
            
            df_updated = pd.DataFrame(updated_movies)
            
            # Generate analysis and save results
            self._generate_analysis(df_updated)
            
            # Save updated data
            df_updated.to_excel(self.output_dir / 'updated_movies.xlsx', index=False)
            logging.info(f"Saved updated data for {len(df_updated)} movies")
            
            return df_updated
            
        except Exception as e:
            logging.error(f"Error updating movie data: {str(e)}")
            raise

    def _process_single_movie(self, title: str) -> Optional[dict]:
        """Process a single movie's data."""
        omdb_data = self.fetch_omdb_data(title)
        if not omdb_data:
            return None
            
        try:
            runtime = int(omdb_data.get('Runtime', '0').split()[0])
            box_office = self._parse_box_office(omdb_data.get('BoxOffice'))
            imdb_rating = float(omdb_data.get('imdbRating', 0))
            imdb_votes = int(omdb_data.get('imdbVotes', '0').replace(',', ''))
            release_date = self._parse_release_date(omdb_data.get('Released'))
            release_year = int(omdb_data.get('Year', 0))
            
            return {
                'title': title,
                'runtime': runtime,
                'box_office': box_office,
                'imdb_rating': imdb_rating,
                'imdb_votes': imdb_votes,
                'release_date': release_date,
                'release_year': release_year
            }
        except Exception as e:
            logging.error(f"Error processing movie {title}: {str(e)}")
            return None

    def _generate_analysis(self, df: pd.DataFrame) -> None:
        """Generate analysis and visualizations."""
        try:
            # Filter relevant movies
            df_filtered = df[
                (df['release_year'] > self.config['analysis']['min_year']) &
                (df['box_office'] > self.config['analysis']['min_box_office'])
            ]
            
            # Generate visualizations
            self._generate_visualizations(df_filtered)
            
            # Calculate and save correlations
            correlations = df_filtered[[
                'runtime', 'box_office', 'imdb_rating', 'imdb_votes'
            ]].corr()
            
            correlations.to_excel(self.output_dir / 'correlations.xlsx')
            
            # Generate summary statistics
            summary_stats = df_filtered.describe()
            summary_stats.to_excel(self.output_dir / 'summary_statistics.xlsx')
            
            # Additional analysis: Box office performance by year
            yearly_stats = df_filtered.groupby('release_year').agg({
                'box_office': ['mean', 'median', 'count'],
                'imdb_rating': 'mean'
            }).round(2)
            
            yearly_stats.to_excel(self.output_dir / 'yearly_analysis.xlsx')
            
            logging.info("Analysis completed and saved")
            
        except Exception as e:
            logging.error(f"Error generating analysis: {str(e)}")
            raise

    def _generate_visualizations(self, df: pd.DataFrame) -> None:
        """Generate analysis visualizations."""
        try:
            # Set style for all plots
            plt.style.use('seaborn')
            
            # 1. Duration vs Box Office
            plt.figure(figsize=(12, 8))
            sns.scatterplot(data=df, x='runtime', y='box_office')
            sns.regplot(data=df, x='runtime', y='box_office', scatter=False, color='red')
            plt.title('Film Duration vs. Box Office Earnings')
            plt.xlabel('Duration (minutes)')
            plt.ylabel('Box Office Earnings ($)')
            plt.savefig(self.output_dir / 'duration_vs_boxoffice.png', dpi=300, bbox_inches='tight')
            plt.close()

            # 2. IMDb Votes vs Ratings
            plt.figure(figsize=(12, 8))
            sns.scatterplot(data=df, x='imdb_votes', y='imdb_rating')
            sns.regplot(data=df, x='imdb_votes', y='imdb_rating', scatter=False, color='red')
            plt.title('IMDb Votes vs. IMDb Ratings')
            plt.xlabel('Number of IMDb Votes')
            plt.ylabel('IMDb Rating')
            plt.savefig(self.output_dir / 'votes_vs_ratings.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 3. Box Office by Year
            plt.figure(figsize=(15, 8))
            yearly_box = df.groupby('release_year')['box_office'].mean()
            yearly_box.plot(kind='bar')
            plt.title('Average Box Office Earnings by Year')
            plt.xlabel('Release Year')
            plt.ylabel('Average Box Office Earnings ($)')
            plt.xticks(rotation=45)
            plt.savefig(self.output_dir / 'yearly_boxoffice.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 4. Rating Distribution
            plt.figure(figsize=(10, 6))
            sns.histplot(data=df, x='imdb_rating', bins=20)
            plt.title('Distribution of IMDb Ratings')
            plt.xlabel('IMDb Rating')
            plt.ylabel('Count')
            plt.savefig(self.output_dir / 'rating_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            logging.info("Generated all visualizations")
            
        except Exception as e:
            logging.error(f"Error generating visualizations: {str(e)}")
            raise

    @staticmethod
    def _parse_box_office(value: str) -> float:
        """Parse box office string to float."""
        if not value or value == 'N/A':
            return 0
        try:
            return float(value.replace('$', '').replace(',', ''))
        except:
            return 0

    @staticmethod
    def _parse_release_date(date_str: str) -> Optional[str]:
        """Parse release date string."""
        if not date_str or date_str == 'N/A':
            return None
        try:
            return datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
        except:
            return None

def main():
    """Main execution function."""
    try:
        analyzer = MovieAnalyzer()
        analyzer.update_movie_data()
        logging.info("Script execution completed successfully")
        
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()