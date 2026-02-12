"""
Deploy updated Mental Health Resources pages (with disclaimer) to FTP.
Uploads all 18 HTML files to /findtorontoevents.ca/MENTALHEALTHRESOURCES/
"""
import os
import sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print('ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required')
    sys.exit(1)

LOCAL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'MENTALHEALTHRESOURCES')
REMOTE_DIR = '/findtorontoevents.ca/MENTALHEALTHRESOURCES'

HTML_FILES = [
    'index.html',
    '5-3-1_Social_Fitness.html',
    '5-4-3-2-1_Grounding.html',
    'Anger_Management.html',
    'Breathing_Exercise.html',
    'Color_Therapy_Game.html',
    'Cyclical_Sighing.html',
    'Demographics.html',
    'Gratitude_Journal.html',
    'Identity_Builder.html',
    'Mindfulness_Meditation.html',
    'Online_Resources.html',
    'Panic_Attack_Relief.html',
    'Progressive_Muscle_Relaxation.html',
    'Quick_Coherence.html',
    'Research_Science.html',
    'Sources_References.html',
    'Vagus_Nerve_Reset.html',
]


def main():
    print(f'Connecting to {FTP_SERVER}...')
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print('Connected and secured.\n')

    # Ensure remote directory exists
    try:
        ftp.cwd(REMOTE_DIR)
    except Exception:
        print(f'Creating remote directory: {REMOTE_DIR}')
        ftp.mkd(REMOTE_DIR)
        ftp.cwd(REMOTE_DIR)

    print(f'Uploading {len(HTML_FILES)} files to {REMOTE_DIR}/\n')

    uploaded = 0
    for filename in HTML_FILES:
        local_path = os.path.join(LOCAL_DIR, filename)
        if not os.path.exists(local_path):
            print(f'  SKIP (not found): {filename}')
            continue

        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            print(f'  UPLOADED: {filename}')
            uploaded += 1
        except Exception as e:
            print(f'  ERROR uploading {filename}: {e}')

    ftp.quit()
    print(f'\nDone! Uploaded {uploaded}/{len(HTML_FILES)} files.')


if __name__ == '__main__':
    main()
