# TuneBot

A Discord music bot with advanced playback controls and Spotify integration.

## Features

### Music Controls
- `..play` or `..p` or `..pl` - Play a song from YouTube or Spotify
- `..queue` or `..q` - Show current queue
- `..skip` or `..s` or `..sk` - Skip current song
- `..stop` - Stop playback and clear queue
- `..pause`, `..resume` - Control playback
- `..volume <0-100>` or `..v` - Adjust volume
- `..nowplaying` or `..np` - Show current song info
- `..playnum <number>` or `..ptn` - Play specific song from queue
- `..shuffle` or `..sh` - Shuffle the queue

### Queue Management
- `..clear` - Clear the queue
- `..remove <number>` or `..rm` - Remove specific song from queue
- `..remove @user` or `..rm @user` - Remove all songs by a user
- `..move <from> <to>` or `..mv` - Move song in queue
- `..loop` or `..lp` - Toggle queue loop

### System Commands
- `..join` - Join your voice channel
- `..leave` or `..le` or `..dis` or `..disconnect` - Leave voice channel
- `..ping` or `..pg` - Check bot latency
- `..help` or `..h` - Show help message

### Spotify Integration
- Support for Spotify tracks and playlists
- Automatic YouTube search for Spotify tracks
- Queue management for playlists

## Technical Details

- Uses discord.py for Discord integration
- yt-dlp for YouTube downloads
- FFmpeg for audio processing
- Async/await for non-blocking operations
- SponsorBlock integration for skipping non-music segments

## Setup

1. Copy the example files: