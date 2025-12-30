# app.py - Flask Web Application
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import re
import json
import time
import yt_dlp
import subprocess
import tempfile
import uuid
import threading
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
os.environ["PATH"] += os.pathsep + "/usr/bin"  # Tambahkan path FFmpeg jika diperlukan

load_dotenv() # Muat variabel dari file .env

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-dev')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['ALLOWED_EXTENSIONS'] = {'txt'}


# In-memory storage for downloads (in production, use database)
download_history = []
active_downloads = {}

class YouTubeDownloader:
    def __init__(self):
        self.quality_options = {
            'mp4_1080': {'name': 'MP4 Full HD (1080p)', 'height': 1080, 'ext': 'mp4', 'type': 'video'},
            'mp4_720': {'name': 'MP4 HD (720p)', 'height': 720, 'ext': 'mp4', 'type': 'video'},
            'mp4_480': {'name': 'MP4 SD (480p)', 'height': 480, 'ext': 'mp4', 'type': 'video'},
            'mp4_360': {'name': 'MP4 Low (360p)', 'height': 360, 'ext': 'mp4', 'type': 'video'},
            'mp3_320': {'name': 'MP3 Ultra HD', 'bitrate': '320k', 'ext': 'mp3', 'type': 'audio'},
            'mp3_256': {'name': 'MP3 High Quality', 'bitrate': '256k', 'ext': 'mp3', 'type': 'audio'},
            'mp3_192': {'name': 'MP3 Standard', 'bitrate': '192k', 'ext': 'mp3', 'type': 'audio'},
            'flac': {'name': 'FLAC Lossless', 'bitrate': '1411k', 'ext': 'flac', 'type': 'audio'},
            'm4a': {'name': 'M4A/AAC', 'bitrate': '256k', 'ext': 'm4a', 'type': 'audio'},
            'opus': {'name': 'OPUS', 'bitrate': '160k', 'ext': 'opus', 'type': 'audio'},
            'wav': {'name': 'WAV', 'bitrate': '1411k', 'ext': 'wav', 'type': 'audio'}
        }
    
    def extract_video_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
            r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def validate_url(self, url):
        """Validate URL (Generic)"""
        # Allow any http/https URL, let yt-dlp handle specific validation
        return url.strip().startswith(('http://', 'https://'))
    
    def get_video_info(self, url):
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                # Tambahkan User-Agent untuk menghindari blokir TikTok/Instagram
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get available formats
                audio_formats = []
                for f in info.get('formats', []):
                    if f.get('acodec') != 'none':
                        audio_formats.append({
                            'format_id': f['format_id'],
                            'ext': f.get('ext', 'unknown'),
                            'abr': f.get('abr') or 0, # Ensure abr is always a number for sorting
                            'format_note': f.get('format_note', ''),
                        })
                
                # Sort by bitrate
                audio_formats.sort(key=lambda x: x['abr'], reverse=True)
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'channel': info.get('channel', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'audio_formats': audio_formats[:5],  # Top 5 formats
                    'description': info.get('description', '')[:200] + '...'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def download_media(self, url, format_key, job_id, user_ip):
        """Download media (audio/video) with specified format"""
        try:
            if format_key not in self.quality_options:
                format_key = 'mp3_320'
            
            quality = self.quality_options[format_key]
            is_video = quality.get('type') == 'video'
            
            # Secara eksplisit temukan path FFmpeg untuk yt-dlp
            import shutil
            ffmpeg_path = shutil.which('ffmpeg')
            
            # Fallback untuk lingkungan hosting di mana PATH mungkin tidak lengkap
            if not ffmpeg_path and os.path.exists('/usr/bin/ffmpeg'):
                ffmpeg_path = '/usr/bin/ffmpeg'
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best', # Default, overridden below
                'outtmpl': os.path.join(tempfile.gettempdir(), f'{job_id}.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'progress_hooks': [self.progress_hook],
                'writethumbnail': True,
                'embedthumbnail': True,
                'addmetadata': True,
                'concurrent_fragment_downloads': 4,
                # Tambahkan User-Agent untuk menghindari blokir TikTok/Instagram
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            }
            
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            if is_video:
                height = quality.get('height', 720)
                ydl_opts.update({
                    'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
                    'merge_output_format': 'mp4',
                })
                # Video postprocessors (metadata only)
                ydl_opts['postprocessors'] = [{
                    'key': 'EmbedThumbnail',
                }, {
                    'key': 'FFmpegMetadata',
                }]
            else:
                # Audio postprocessors
                ydl_opts['format'] = 'bestaudio/best'
                if quality['ext'] == 'mp3':
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality['bitrate'], # Gunakan bitrate langsung
                    }, {
                        'key': 'EmbedThumbnail',
                    }, {
                        'key': 'FFmpegMetadata',
                    }]
                
                elif quality['ext'] == 'flac':
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'flac',
                    }, {
                        'key': 'EmbedThumbnail',
                    }]
            
            # Update status
            active_downloads[job_id] = {
                'status': 'processing',
                'progress': 0,
                'filename': '',
                'message': 'Starting download...'
            }
            
            # Start download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get the final file path from the info dict after post-processing
                final_filepath = info.get('requested_downloads', [{}])[0].get('filepath')

                active_downloads[job_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'filename': os.path.basename(final_filepath),
                    'filepath': final_filepath,
                    'filesize': os.path.getsize(final_filepath) if final_filepath and os.path.exists(final_filepath) else 0,
                    'title': info.get('title', 'Unknown'),
                    'quality': quality['name']
                })
                
                # Add to history
                download_history.append({
                    'job_id': job_id,
                    'url': url,
                    'title': info.get('title', 'Unknown'),
                    'quality': quality['name'],
                    'timestamp': datetime.now().isoformat(),
                    'user_ip': user_ip,
                    'filesize': active_downloads[job_id]['filesize']
                })
                
                return True
                
        except Exception as e:
            active_downloads[job_id] = {
                'status': 'error',
                'progress': 0,
                'message': str(e)
            }
            return False
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Try to get percentage
            if '_percent_str' in d:
                percent = d['_percent_str'].strip().replace('%', '')
                try:
                    progress = float(percent)
                    # Update progress for active downloads
                    for job_id in active_downloads:
                        if active_downloads[job_id]['status'] == 'processing':
                            active_downloads[job_id]['progress'] = progress
                            active_downloads[job_id]['message'] = f"Downloading... {progress:.1f}%"
                except:
                    pass

downloader = YouTubeDownloader()

def cleanup_old_files():
    """Background task to clean up old files and history every 24 hours"""
    global download_history
    while True:
        try:
            temp_dir = tempfile.gettempdir()
            now = time.time()
            cutoff = now - 86400  # 24 hours in seconds
            
            # Extensions created by the app
            valid_extensions = {'.mp3', '.mp4', '.flac', '.m4a', '.opus', '.wav', '.webm', '.part', '.ytdl'}
            
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in valid_extensions:
                        # Check if it looks like a UUID (length 36 with hyphens) - to avoid deleting system files
                        name_part = os.path.splitext(filename)[0]
                        if len(name_part) == 36 and '-' in name_part:
                            if os.path.getmtime(file_path) < cutoff:
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    print(f"Error deleting old file {filename}: {e}")
            
            # Cleanup history older than 24 hours
            cutoff_dt = datetime.fromtimestamp(cutoff)
            # Filter history keeping only items newer than cutoff
            new_history = []
            for item in download_history:
                try:
                    # Parse timestamp from string
                    item_dt = datetime.fromisoformat(item['timestamp'])
                    if item_dt > cutoff_dt:
                        new_history.append(item)
                except (ValueError, TypeError):
                    pass
            
            download_history = new_history
            
        except Exception as e:
            print(f"Cleanup task error: {e}")
        
        # Check every hour
        time.sleep(3600)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_job_id():
    return str(uuid.uuid4())

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html', 
                         quality_options=downloader.quality_options,
                         recent_downloads=download_history[-10:])

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information API"""
    url = request.json.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL required'})
    
    if not downloader.validate_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'})
    
    info = downloader.get_video_info(url)
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def start_download():
    """Start download process"""
    url = request.json.get('url', '')
    format_key = request.json.get('format', 'mp3_320')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL required'})
    
    if not downloader.validate_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'})
    
    # Generate job ID
    job_id = generate_job_id()
    user_ip = get_client_ip()
    
    # Start download in background thread
    thread = threading.Thread(
        target=downloader.download_media,
        args=(url, format_key, job_id, user_ip)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Download started in background'
    })

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get download status"""
    if job_id in active_downloads:
        return jsonify(active_downloads[job_id])
    return jsonify({'status': 'not_found'})

@app.route('/api/download-file/<job_id>')
def download_file(job_id):
    """Download completed file"""
    if job_id in active_downloads and active_downloads[job_id]['status'] == 'completed':
        filepath = active_downloads[job_id]['filepath']
        original_filename = active_downloads[job_id]['filename'] # e.g., UUID.mp3
        song_title = active_downloads[job_id].get('title', 'download')
        
        # Sanitize the song title to create a valid filename
        file_extension = os.path.splitext(original_filename)[1]
        download_name = f"{secure_filename(song_title)}{file_extension}"
        
        # Menentukan mimetype secara dinamis
        mimetype = 'application/octet-stream'
        mimetypes = {'mp3': 'audio/mpeg', 'flac': 'audio/flac', 'm4a': 'audio/mp4', 'wav': 'audio/wav', 'opus': 'audio/opus', 'mp4': 'video/mp4'}
        mimetype = mimetypes.get(file_extension.strip('.'), 'application/octet-stream')

        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=download_name, mimetype=mimetype)
    
    return "File not found", 404

@app.route('/api/batch-download', methods=['POST'])
def batch_download():
    """Handle batch download from file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    format_key = request.form.get('format', 'mp3_320')
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type'})
    
    # Save uploaded file
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(temp_path)
    
    # Read URLs from file
    urls = []
    with open(temp_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and downloader.validate_url(line):
                urls.append(line)
    
    # Start batch downloads
    job_ids = []
    user_ip = get_client_ip()
    
    for url in urls[:10]:  # Limit to 10 URLs
        job_id = generate_job_id()
        thread = threading.Thread(
            target=downloader.download_media,
            args=(url, format_key, job_id, user_ip)
        )
        thread.daemon = True
        thread.start()
        job_ids.append(job_id)
    
    # Clean up temp file
    os.remove(temp_path)
    
    return jsonify({
        'success': True,
        'job_ids': job_ids,
        'count': len(job_ids),
        'message': f'Started {len(job_ids)} downloads'
    })

@app.route('/api/history')
def get_history():
    """Get download history for current user"""
    user_ip = get_client_ip()
    user_history = [d for d in download_history if d['user_ip'] == user_ip]
    return jsonify({'history': user_history[-20:]})

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear user's download history"""
    user_ip = get_client_ip()
    global download_history
    
    # Keep only history from other users
    download_history = [d for d in download_history if d['user_ip'] != user_ip]
    
    return jsonify({'success': True, 'message': 'History cleared'})

@app.route('/api/system-status')
def system_status():
    """Get system status"""
    # Get disk space
    import shutil
    # Check if FFmpeg is available in the system's PATH
    ffmpeg_path = shutil.which('ffmpeg')
    # Fallback untuk lingkungan hosting
    if not ffmpeg_path and os.path.exists('/usr/bin/ffmpeg'):
        ffmpeg_path = '/usr/bin/ffmpeg'
        
    ffmpeg_available = ffmpeg_path is not None
    total, used, free = shutil.disk_usage(".")
    
    return jsonify({
        'ffmpeg_available': ffmpeg_available,
        'disk_space': {
            'total': total,
            'used': used,
            'free': free,
            'free_gb': free // (2**30)
        },
        'active_downloads': len([d for d in active_downloads.values() if d['status'] == 'processing']),
        'total_downloads': len(download_history)
    })

@app.route('/api/check-dependencies')
def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'flask',
        'gunicorn',
        'requests',
        'python-dotenv',
        'sqlalchemy',
        'psycopg2-binary',
        'yt-dlp'
    ]
    
    installed_packages = []
    try:
        import pkg_resources
        installed_packages = [dist.project_name.lower() for dist in pkg_resources.working_set]
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
    missing_packages = [pkg for pkg in required_packages if pkg not in installed_packages]
    
    if missing_packages:
        return jsonify({
            'success': False,
            'message': 'Beberapa dependensi belum terinstall',
            'missing_packages': missing_packages
        })
    else:
        return jsonify({
            'success': True, 'message': 'Semua dependensi telah terinstall'
        })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
    cleanup_thread.start()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)