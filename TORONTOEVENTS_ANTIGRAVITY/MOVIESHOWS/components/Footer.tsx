/**
 * UPDATE #60: Footer Component
 * Site footer with links and info
 */

import React from 'react';

export function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="site-footer">
            <div className="footer-content">
                <div className="footer-section">
                    <h4>MovieShows</h4>
                    <p>Your ultimate destination for discovering and watching movie trailers.</p>
                </div>

                <div className="footer-section">
                    <h4>Quick Links</h4>
                    <ul>
                        <li><a href="/">Home</a></li>
                        <li><a href="/movies">Movies</a></li>
                        <li><a href="/tv-shows">TV Shows</a></li>
                        <li><a href="/queue">My Queue</a></li>
                    </ul>
                </div>

                <div className="footer-section">
                    <h4>Resources</h4>
                    <ul>
                        <li><a href="/about">About</a></li>
                        <li><a href="/privacy">Privacy Policy</a></li>
                        <li><a href="/terms">Terms of Service</a></li>
                        <li><a href="/contact">Contact</a></li>
                    </ul>
                </div>

                <div className="footer-section">
                    <h4>Connect</h4>
                    <div className="social-links">
                        <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">🐦 Twitter</a>
                        <a href="https://facebook.com" target="_blank" rel="noopener noreferrer">📘 Facebook</a>
                        <a href="https://instagram.com" target="_blank" rel="noopener noreferrer">📷 Instagram</a>
                    </div>
                </div>
            </div>

            <div className="footer-bottom">
                <p>&copy; {currentYear} MovieShows. All rights reserved.</p>
                <p>Made with ❤️ for movie lovers</p>
            </div>
        </footer>
    );
}

const styles = `
.site-footer {
  background: rgba(0, 0, 0, 0.5);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: 4rem;
  padding: 3rem 2rem 1rem;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto 2rem;
}

.footer-section h4 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
  color: #667eea;
}

.footer-section p {
  margin: 0;
  opacity: 0.7;
  line-height: 1.6;
}

.footer-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-section li {
  margin-bottom: 0.5rem;
}

.footer-section a {
  color: white;
  text-decoration: none;
  opacity: 0.7;
  transition: all 0.2s;
}

.footer-section a:hover {
  opacity: 1;
  color: #667eea;
}

.social-links {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.footer-bottom {
  text-align: center;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  opacity: 0.6;
  font-size: 0.9rem;
}

.footer-bottom p {
  margin: 0.25rem 0;
}

@media (max-width: 768px) {
  .footer-content {
    grid-template-columns: 1fr;
  }
}
`;
