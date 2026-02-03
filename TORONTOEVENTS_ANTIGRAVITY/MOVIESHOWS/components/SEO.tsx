/**
 * UPDATE #44: SEO Component
 * Meta tags for social sharing
 */

import React from 'react';
import { Helmet } from 'react-helmet-async';

interface SEOProps {
    title: string;
    description: string;
    image?: string;
    url?: string;
    type?: 'website' | 'article' | 'video.movie';
}

export function SEO({
    title,
    description,
    image = 'https://findtorontoevents.ca/MOVIESHOWS/og-image.jpg',
    url = 'https://findtorontoevents.ca/MOVIESHOWS',
    type = 'website'
}: SEOProps) {
    const fullTitle = `${title} | MovieShows`;

    return (
        <Helmet>
            {/* Primary Meta Tags */}
            <title>{fullTitle}</title>
            <meta name="title" content={fullTitle} />
            <meta name="description" content={description} />

            {/* Open Graph / Facebook */}
            <meta property="og:type" content={type} />
            <meta property="og:url" content={url} />
            <meta property="og:title" content={fullTitle} />
            <meta property="og:description" content={description} />
            <meta property="og:image" content={image} />

            {/* Twitter */}
            <meta property="twitter:card" content="summary_large_image" />
            <meta property="twitter:url" content={url} />
            <meta property="twitter:title" content={fullTitle} />
            <meta property="twitter:description" content={description} />
            <meta property="twitter:image" content={image} />

            {/* Additional */}
            <meta name="robots" content="index, follow" />
            <meta name="language" content="English" />
            <link rel="canonical" href={url} />
        </Helmet>
    );
}
