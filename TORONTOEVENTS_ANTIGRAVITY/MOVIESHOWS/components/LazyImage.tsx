/**
 * UPDATE #42: Image Lazy Loading Component
 * Intersection Observer for performance
 */

import React, { useEffect, useRef, useState } from 'react';

interface LazyImageProps {
    src: string;
    alt: string;
    placeholder?: string;
    className?: string;
    onLoad?: () => void;
    onError?: () => void;
}

export function LazyImage({
    src,
    alt,
    placeholder = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"%3E%3Crect fill="%23222" width="400" height="300"/%3E%3C/svg%3E',
    className = '',
    onLoad,
    onError
}: LazyImageProps) {
    const [imageSrc, setImageSrc] = useState(placeholder);
    const [isLoaded, setIsLoaded] = useState(false);
    const imgRef = useRef<HTMLImageElement>(null);

    useEffect(() => {
        if (!imgRef.current) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setImageSrc(src);
                        observer.disconnect();
                    }
                });
            },
            {
                rootMargin: '50px', // Start loading 50px before visible
                threshold: 0.01
            }
        );

        observer.observe(imgRef.current);

        return () => observer.disconnect();
    }, [src]);

    const handleLoad = () => {
        setIsLoaded(true);
        onLoad?.();
    };

    const handleError = () => {
        setImageSrc(placeholder);
        onError?.();
    };

    return (
        <img
            ref={imgRef}
            src={imageSrc}
            alt={alt}
            className={`lazy-image ${isLoaded ? 'loaded' : 'loading'} ${className}`}
            onLoad={handleLoad}
            onError={handleError}
            loading="lazy"
        />
    );
}

const styles = `
.lazy-image {
  transition: opacity 0.3s ease-in-out;
}

.lazy-image.loading {
  opacity: 0.5;
  filter: blur(5px);
}

.lazy-image.loaded {
  opacity: 1;
  filter: blur(0);
}
`;
