import streamlit as st
from googleapiclient.discovery import build
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from datetime import datetime
import re

# Initialize YouTube API
api_key = 'AIzaSyDbBkgiu06N_SCAEDc3ffzlL5YLbi_GTNw'
youtube = build('youtube', 'v3', developerKey=api_key)

# Function to extract playlist ID from URL
def extract_playlist_id(url):
    match = re.search(r"list=([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

# Function to retrieve playlist videos statistics and comments
def get_playlist_videos_and_comments(playlist_id):
    videos_data = []
    all_comments = []
    request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50)
    response = request.execute()
    
    for item in response['items']:
        video_id = item['snippet']['resourceId']['videoId']
        video_date = item['snippet']['publishedAt']
        
        # Get statistics for each video
        video_request = youtube.videos().list(part="statistics", id=video_id)
        video_response = video_request.execute()
        
        if video_response['items']:
            video_stats = video_response['items'][0]['statistics']
            videos_data.append({
                "video_id": video_id,
                "date": datetime.strptime(video_date, "%Y-%m-%dT%H:%M:%SZ"),
                "view_count": int(video_stats.get('viewCount', 0)),
                "like_count": int(video_stats.get('likeCount', 0)),
                "comment_count": int(video_stats.get('commentCount', 0))
            })
            
            # Collect comments for sentiment analysis
            comments = get_video_comments(video_id)
            all_comments.extend(comments)
    
    return pd.DataFrame(videos_data), all_comments

# Function to retrieve comments for a video
def get_video_comments(video_id):
    comments = []
    request = youtube.commentThreads().list(part="snippet", videoId=video_id, textFormat="plainText")
    response = request.execute()
    
    for item in response['items']:
        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
        comments.append(comment)
    
    return comments

# Function to analyze sentiments using VADER
def analyze_sentiments(comments):
    analyzer = SentimentIntensityAnalyzer()
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}

    for comment in comments:
        score = analyzer.polarity_scores(comment)
        if score['compound'] >= 0.05:
            sentiments['positive'] += 1
        elif score['compound'] <= -0.05:
            sentiments['negative'] += 1
        else:
            sentiments['neutral'] += 1

    return pd.DataFrame.from_dict(sentiments, orient='index', columns=['Count'])

# Function to retrieve channel details
def get_channel_details(video_id):
    video_request = youtube.videos().list(part="snippet", id=video_id)
    video_response = video_request.execute()
    
    if video_response['items']:
        channel_id = video_response['items'][0]['snippet']['channelId']
        channel_request = youtube.channels().list(part="snippet,statistics", id=channel_id)
        channel_response = channel_request.execute()
        
        if channel_response['items']:
            channel_info = channel_response['items'][0]
            return {
                "channel_title": channel_info['snippet']['title'],
                "channel_description": channel_info['snippet']['description'],
                "subscriber_count": int(channel_info['statistics']['subscriberCount']),
                "view_count": int(channel_info['statistics']['viewCount']),
                "video_count": int(channel_info['statistics']['videoCount']),
            }
    return None

# Visualization of playlist metrics over time using Plotly
def plot_metrics(df):
    # Create an interactive line chart using Plotly
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['date'], y=df['view_count'], mode='lines+markers', name='Views'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['like_count'], mode='lines+markers', name='Likes'))
    
    fig.update_layout(title='Playlist Metrics Over Time', xaxis_title='Date', yaxis_title='Count')
    st.plotly_chart(fig)

# Visualization of channel stats using Plotly
# Visualization of channel stats using Plotly
def plot_channel_stats(channel_info):
    # Create an interactive bar chart using Plotly
    fig = go.Figure(data=[
        go.Bar(
            name='Subscribers',
            x=['Subscribers'],
            y=[channel_info['subscriber_count']],
            hoverinfo='text',
            text=f"{channel_info['subscriber_count']} Subscribers"
        ),
        go.Bar(
            name='Total Views',
            x=['Total Views'],
            y=[channel_info['view_count']],
            hoverinfo='text',
            text=f"{channel_info['view_count']} Total Views"
        ),
        go.Bar(
            name='Total Videos',
            x=['Total Videos'],
            y=[channel_info['video_count']],
            hoverinfo='text',
            text=f"{channel_info['video_count']} Total Videos"
        )
    ])
    
    fig.update_layout(barmode='group', title='Channel Statistics', yaxis_title='Count')
    st.plotly_chart(fig)


# Streamlit UI
st.title("YouTube Analytica")

playlist_url = st.text_input("Enter YouTube Playlist URL:")

if st.button("Analyze Playlist"):
    playlist_id = extract_playlist_id(playlist_url)
    
    if playlist_id:
        # Retrieve video stats and comments from the playlist
        df_videos_stats, all_comments = get_playlist_videos_and_comments(playlist_id)
        
        # Plot playlist metrics over time
        st.subheader("Playlist Metrics Over Time")
        plot_metrics(df_videos_stats)

        # Get channel details from the first video in the playlist
        if not df_videos_stats.empty:
            channel_info = get_channel_details(df_videos_stats['video_id'].iloc[0])
            if channel_info:
                st.subheader("Channel Details")
                st.write(f"**Channel Title:** {channel_info['channel_title']}")
                st.write(f"**Channel Description:** {channel_info['channel_description']}")
                st.write(f"**Subscribers:** {channel_info['subscriber_count']}")
                st.write(f"**Total Views:** {channel_info['view_count']}")
                st.write(f"**Total Videos:** {channel_info['video_count']}")
                
                # Plot channel stats
                plot_channel_stats(channel_info)

        # Perform sentiment analysis on all comments in the playlist
        if all_comments:
            sentiment_results = analyze_sentiments(all_comments)
            st.write("Sentiment Analysis Results for Entire Playlist:")
            st.write(sentiment_results)
            st.bar_chart(sentiment_results)
        else:
            st.write("No comments found for sentiment analysis.")
    else:
        st.write("Invalid playlist URL. Please enter a valid YouTube playlist URL.")
