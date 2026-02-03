/**
 * UPDATE #92: SEO Optimizer
 * Advanced SEO utilities
 */

interface SEOConfig {
    title: string;
    description: string;
    keywords?: string[];
    image?: string;
    url?: string;
    type?: 'website' | 'article' | 'video';
    author?: string;
    publishedTime?: string;
    modifiedTime?: string;
}

class SEOOptimizer {
    /**
     * Generate meta tags
     */
    generateMetaTags(config: SEOConfig): string {
        const tags: string[] = [];

        // Basic meta tags
        tags.push(`<title>${this.escapeHtml(config.title)}</title>`);
        tags.push(`<meta name="description" content="${this.escapeHtml(config.description)}">`);

        if (config.keywords && config.keywords.length > 0) {
            tags.push(`<meta name="keywords" content="${config.keywords.join(', ')}">`);
        }

        // Open Graph
        tags.push(`<meta property="og:title" content="${this.escapeHtml(config.title)}">`);
        tags.push(`<meta property="og:description" content="${this.escapeHtml(config.description)}">`);
        tags.push(`<meta property="og:type" content="${config.type || 'website'}">`);

        if (config.url) {
            tags.push(`<meta property="og:url" content="${config.url}">`);
        }

        if (config.image) {
            tags.push(`<meta property="og:image" content="${config.image}">`);
        }

        // Twitter Card
        tags.push(`<meta name="twitter:card" content="summary_large_image">`);
        tags.push(`<meta name="twitter:title" content="${this.escapeHtml(config.title)}">`);
        tags.push(`<meta name="twitter:description" content="${this.escapeHtml(config.description)}">`);

        if (config.image) {
            tags.push(`<meta name="twitter:image" content="${config.image}">`);
        }

        // Article metadata
        if (config.type === 'article') {
            if (config.author) {
                tags.push(`<meta property="article:author" content="${this.escapeHtml(config.author)}">`);
            }
            if (config.publishedTime) {
                tags.push(`<meta property="article:published_time" content="${config.publishedTime}">`);
            }
            if (config.modifiedTime) {
                tags.push(`<meta property="article:modified_time" content="${config.modifiedTime}">`);
            }
        }

        return tags.join('\n');
    }

    /**
     * Generate JSON-LD structured data
     */
    generateStructuredData(type: 'Movie' | 'WebSite' | 'Organization', data: any): string {
        const structuredData = {
            '@context': 'https://schema.org',
            '@type': type,
            ...data
        };

        return `<script type="application/ld+json">${JSON.stringify(structuredData, null, 2)}</script>`;
    }

    /**
     * Generate sitemap entry
     */
    generateSitemapEntry(url: string, lastmod?: string, priority?: number): string {
        return `
  <url>
    <loc>${url}</loc>
    ${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}
    ${priority ? `<priority>${priority}</priority>` : ''}
    <changefreq>weekly</changefreq>
  </url>`;
    }

    /**
     * Generate robots.txt
     */
    generateRobotsTxt(sitemapUrl: string, disallowPaths: string[] = []): string {
        const lines = ['User-agent: *'];

        disallowPaths.forEach(path => {
            lines.push(`Disallow: ${path}`);
        });

        lines.push('');
        lines.push(`Sitemap: ${sitemapUrl}`);

        return lines.join('\n');
    }

    /**
     * Optimize title for SEO
     */
    optimizeTitle(title: string, siteName: string = 'MovieShows'): string {
        const maxLength = 60;
        const separator = ' | ';

        if (title.length + separator.length + siteName.length <= maxLength) {
            return `${title}${separator}${siteName}`;
        }

        const availableLength = maxLength - separator.length - siteName.length - 3; // 3 for '...'
        return `${title.substring(0, availableLength)}...${separator}${siteName}`;
    }

    /**
     * Optimize description for SEO
     */
    optimizeDescription(description: string): string {
        const maxLength = 160;

        if (description.length <= maxLength) {
            return description;
        }

        return description.substring(0, maxLength - 3) + '...';
    }

    private escapeHtml(text: string): string {
        const map: Record<string, string> = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };

        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

export const seoOptimizer = new SEOOptimizer();

/**
 * React hook for SEO
 */
import { useEffect } from 'react';

export function useSEO(config: SEOConfig) {
    useEffect(() => {
        // Update title
        document.title = seoOptimizer.optimizeTitle(config.title);

        // Update meta description
        let metaDescription = document.querySelector('meta[name="description"]');
        if (!metaDescription) {
            metaDescription = document.createElement('meta');
            metaDescription.setAttribute('name', 'description');
            document.head.appendChild(metaDescription);
        }
        metaDescription.setAttribute('content', seoOptimizer.optimizeDescription(config.description));

        // Update Open Graph tags
        const updateMetaTag = (property: string, content: string) => {
            let tag = document.querySelector(`meta[property="${property}"]`);
            if (!tag) {
                tag = document.createElement('meta');
                tag.setAttribute('property', property);
                document.head.appendChild(tag);
            }
            tag.setAttribute('content', content);
        };

        updateMetaTag('og:title', config.title);
        updateMetaTag('og:description', config.description);
        if (config.image) updateMetaTag('og:image', config.image);
        if (config.url) updateMetaTag('og:url', config.url);
    }, [config]);
}
