/**
 * UPDATE #46: Social Share Component
 * Share to social media platforms
 */

import React from 'react';

interface ShareButtonsProps {
    url: string;
    title: string;
    description?: string;
}

export function ShareButtons({ url, title, description = '' }: ShareButtonsProps) {
    const encodedUrl = encodeURIComponent(url);
    const encodedTitle = encodeURIComponent(title);
    const encodedDesc = encodeURIComponent(description);

    const shareLinks = {
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
        twitter: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`,
        reddit: `https://reddit.com/submit?url=${encodedUrl}&title=${encodedTitle}`,
        whatsapp: `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`,
        telegram: `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`,
        email: `mailto:?subject=${encodedTitle}&body=${encodedDesc}%20${encodedUrl}`
    };

    const handleShare = async () => {
        if (navigator.share) {
            try {
                await navigator.share({
                    title,
                    text: description,
                    url
                });
            } catch (error) {
                console.log('Share cancelled');
            }
        }
    };

    const handleCopyLink = () => {
        navigator.clipboard.writeText(url);
        alert('Link copied to clipboard!');
    };

    return (
        <div className="share-buttons">
            <h4>Share this movie</h4>

            <div className="share-grid">
                <a href={shareLinks.facebook} target="_blank" rel="noopener noreferrer" className="share-btn facebook">
                    📘 Facebook
                </a>
                <a href={shareLinks.twitter} target="_blank" rel="noopener noreferrer" className="share-btn twitter">
                    🐦 Twitter
                </a>
                <a href={shareLinks.reddit} target="_blank" rel="noopener noreferrer" className="share-btn reddit">
                    🔴 Reddit
                </a>
                <a href={shareLinks.whatsapp} target="_blank" rel="noopener noreferrer" className="share-btn whatsapp">
                    💬 WhatsApp
                </a>
                <a href={shareLinks.telegram} target="_blank" rel="noopener noreferrer" className="share-btn telegram">
                    ✈️ Telegram
                </a>
                <a href={shareLinks.email} className="share-btn email">
                    📧 Email
                </a>
            </div>

            <div className="share-actions">
                {navigator.share && (
                    <button onClick={handleShare} className="share-native">
                        📤 Share
                    </button>
                )}
                <button onClick={handleCopyLink} className="copy-link">
                    🔗 Copy Link
                </button>
            </div>
        </div>
    );
}

const styles = `
.share-buttons {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
}

.share-buttons h4 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
}

.share-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.share-btn {
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  text-decoration: none;
  text-align: center;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.share-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.share-actions {
  display: flex;
  gap: 0.75rem;
}

.share-native,
.copy-link {
  flex: 1;
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.share-native:hover,
.copy-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
`;
