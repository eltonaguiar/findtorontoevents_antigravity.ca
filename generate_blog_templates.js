// Template Generator Script - Powered by antigravity
// This script generates all 50 blog templates with unique themes

const fs = require('fs');
const path = require('path');

const templates = [
    // Glassmorphism & Modern (300-309)
    { num: 300, theme: 'Classic Glassmorphism', bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', style: 'glass' },
    { num: 301, theme: 'Neon Glassmorphism', bg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', style: 'neon-glass' },
    { num: 302, theme: 'Dark Glassmorphism', bg: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)', style: 'dark-glass' },
    { num: 303, theme: 'Minimalist Glass', bg: 'linear-gradient(135deg, #e0e0e0 0%, #f5f5f5 100%)', style: 'minimal-glass' },
    { num: 304, theme: 'Multi-Layer Glass', bg: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', style: 'multi-glass' },
    { num: 305, theme: 'Particle Glass', bg: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)', style: 'particle-glass' },
    { num: 306, theme: 'Holographic Glass', bg: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', style: 'holo-glass' },
    { num: 307, theme: '3D Tilt Glass', bg: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)', style: 'tilt-glass' },
    { num: 308, theme: 'Neumorphism Glass', bg: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', style: 'neuro-glass' },
    { num: 309, theme: 'Liquid Glass', bg: 'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)', style: 'liquid-glass' },

    // Cyberpunk & Neon (310-319)
    { num: 310, theme: 'Classic Cyberpunk', bg: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)', style: 'cyberpunk' },
    { num: 311, theme: 'Matrix Code', bg: 'linear-gradient(135deg, #000000 0%, #0a0a0a 100%)', style: 'matrix' },
    { num: 312, theme: 'Glitch Cyberpunk', bg: 'linear-gradient(135deg, #141e30 0%, #243b55 100%)', style: 'glitch' },
    { num: 313, theme: 'Holographic UI', bg: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', style: 'holo-ui' },
    { num: 314, theme: 'Synthwave Grid', bg: 'linear-gradient(135deg, #2b1055 0%, #7597de 100%)', style: 'synthwave' },
    { num: 315, theme: 'Dystopian Dark', bg: 'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)', style: 'dystopian' },
    { num: 316, theme: 'Blade Runner', bg: 'linear-gradient(135deg, #000000 0%, #434343 100%)', style: 'blade-runner' },
    { num: 317, theme: 'Tron Lights', bg: 'linear-gradient(135deg, #000000 0%, #0a192f 100%)', style: 'tron' },
    { num: 318, theme: 'Cyber Terminal', bg: 'linear-gradient(135deg, #0d0d0d 0%, #1a1a1a 100%)', style: 'terminal' },
    { num: 319, theme: 'Neon Tokyo', bg: 'linear-gradient(135deg, #ff0080 0%, #7928ca 100%)', style: 'tokyo' },

    // Brutalist & Minimal (320-329)
    { num: 320, theme: 'Raw Brutalist', bg: '#f5f5f5', style: 'brutalist' },
    { num: 321, theme: 'Neo-Brutalist', bg: 'linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%)', style: 'neo-brutalist' },
    { num: 322, theme: 'Swiss Minimal', bg: '#ffffff', style: 'swiss' },
    { num: 323, theme: 'Bauhaus Geometric', bg: 'linear-gradient(135deg, #ee5a6f 0%, #f29263 100%)', style: 'bauhaus' },
    { num: 324, theme: 'Monochrome', bg: '#000000', style: 'monochrome' },
    { num: 325, theme: 'Grid Heavy', bg: '#e8e8e8', style: 'grid' },
    { num: 326, theme: 'Deconstructed', bg: 'linear-gradient(135deg, #d3cce3 0%, #e9e4f0 100%)', style: 'deconstructed' },
    { num: 327, theme: 'Terminal CLI', bg: '#0c0c0c', style: 'cli' },
    { num: 328, theme: 'Newspaper Print', bg: '#f9f9f9', style: 'newspaper' },
    { num: 329, theme: 'Stark Contrast', bg: '#ffffff', style: 'stark' },

    // Experimental & 3D (330-339)
    { num: 330, theme: 'Parallax 3D', bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', style: 'parallax' },
    { num: 331, theme: 'Isometric 3D', bg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', style: 'isometric' },
    { num: 332, theme: 'WebGL Particles', bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', style: 'webgl' },
    { num: 333, theme: '3D Carousel', bg: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', style: 'carousel-3d' },
    { num: 334, theme: 'Floating Islands', bg: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', style: 'islands' },
    { num: 335, theme: 'VR Immersive', bg: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)', style: 'vr' },
    { num: 336, theme: 'Origami Fold', bg: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', style: 'origami' },
    { num: 337, theme: 'Liquid Metal', bg: 'linear-gradient(135deg, #d299c2 0%, #fef9d7 100%)', style: 'liquid-metal' },
    { num: 338, theme: 'Kaleidoscope', bg: 'linear-gradient(135deg, #f5576c 0%, #f093fb 100%)', style: 'kaleidoscope' },
    { num: 339, theme: 'Generative Art', bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', style: 'generative' },

    // Retro & Vintage (340-349)
    { num: 340, theme: '80s Arcade', bg: 'linear-gradient(135deg, #f857a6 0%, #ff5858 100%)', style: 'arcade' },
    { num: 341, theme: 'Vaporwave', bg: 'linear-gradient(135deg, #ff6ec4 0%, #7873f5 100%)', style: 'vaporwave' },
    { num: 342, theme: 'Windows 95', bg: '#008080', style: 'win95' },
    { num: 343, theme: 'Retro Terminal', bg: '#000000', style: 'retro-terminal' },
    { num: 344, theme: 'Art Deco', bg: 'linear-gradient(135deg, #d4af37 0%, #f4e4c1 100%)', style: 'art-deco' },
    { num: 345, theme: '70s Psychedelic', bg: 'linear-gradient(135deg, #ff9966 0%, #ff5e62 100%)', style: 'psychedelic' },
    { num: 346, theme: 'Vintage Poster', bg: 'linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%)', style: 'vintage-poster' },
    { num: 347, theme: 'Cassette Player', bg: 'linear-gradient(135deg, #434343 0%, #000000 100%)', style: 'cassette' },
    { num: 348, theme: 'Classified Ads', bg: '#f5f5dc', style: 'classified' },
    { num: 349, theme: 'Retro Futurism', bg: 'linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)', style: 'retro-future' }
];

function generateTemplate(config) {
    const { num, theme, bg, style } = config;

    // Generate unique styles based on theme category
    let customStyles = '';
    let cardStyles = '';

    if (style.includes('glass')) {
        customStyles = `
      .filters-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
      }
      .event-card {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.18);
      }
      .event-card:hover {
        background: rgba(255, 255, 255, 0.18);
        transform: translateY(-8px) scale(1.02);
      }
    `;
    } else if (style.includes('cyberpunk') || style.includes('neon') || style === 'matrix' || style === 'glitch') {
        customStyles = `
      .filters-container {
        background: rgba(0, 212, 255, 0.05);
        border: 2px solid #00d4ff;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
      }
      .event-card {
        background: rgba(0, 0, 0, 0.6);
        border: 2px solid #ff00ff;
        box-shadow: 0 0 15px rgba(255, 0, 255, 0.4);
      }
      .event-card:hover {
        border-color: #00d4ff;
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.6);
        transform: translateY(-5px);
      }
      .event-card h3 {
        color: #00d4ff;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
      }
    `;
    } else if (style.includes('brutalist') || style === 'swiss' || style === 'monochrome') {
        customStyles = `
      .filters-container {
        background: ${style === 'monochrome' ? '#1a1a1a' : '#ffffff'};
        border: 4px solid ${style === 'monochrome' ? '#ffffff' : '#000000'};
        border-radius: 0;
      }
      .event-card {
        background: ${style === 'monochrome' ? '#000000' : '#f5f5f5'};
        border: 3px solid ${style === 'monochrome' ? '#ffffff' : '#000000'};
        border-radius: 0;
      }
      .event-card:hover {
        transform: translate(5px, -5px);
        box-shadow: -8px 8px 0 ${style === 'monochrome' ? '#ffffff' : '#000000'};
      }
      .event-card h3 {
        color: ${style === 'monochrome' ? '#ffffff' : '#000000'};
        font-weight: 900;
        text-transform: uppercase;
      }
    `;
    } else {
        // Default experimental/retro styles
        customStyles = `
      .filters-container {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(15px);
        border: 2px solid rgba(255, 255, 255, 0.15);
      }
      .event-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
      }
      .event-card:hover {
        transform: scale(1.05) rotate(2deg);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
      }
    `;
    }

    return `<!-- Designed by antigravity -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="generator" content="antigravity">
  <meta name="description" content="Toronto Events - ${theme}">
  <title>Toronto Events - Blog ${num} | ${theme}</title>
  <link rel="stylesheet" href="blog_styles_common.css">
  <style>
    /* Styled by antigravity */
    body {
      background: ${bg};
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .page-header {
      text-align: center;
      margin-bottom: 3rem;
      animation: fadeIn 0.8s ease;
    }

    .page-header h1 {
      font-size: 3rem;
      font-weight: 800;
      color: ${style.includes('brutalist') || style === 'monochrome' ? (style === 'monochrome' ? '#ffffff' : '#000000') : '#ffffff'};
      margin-bottom: 0.5rem;
    }

    .page-header p {
      color: ${style.includes('brutalist') || style === 'monochrome' ? (style === 'monochrome' ? '#cccccc' : '#333333') : 'rgba(255, 255, 255, 0.9)'};
      font-size: 1.125rem;
      font-weight: 500;
    }

    .main-container {
      max-width: 1400px;
      margin: 0 auto;
    }

    ${customStyles}

    .filters-container {
      border-radius: ${style.includes('brutalist') ? '0' : '24px'};
      padding: 2rem;
      margin-bottom: 2rem;
    }

    .filters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
    }

    .filter-group input,
    .filter-group select {
      background: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.25);
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#000000' : '#ffffff'};
      padding: 0.75rem 1rem;
      border-radius: ${style.includes('brutalist') ? '0' : '12px'};
      font-size: 0.9375rem;
    }

    .filter-group label {
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#000000' : 'rgba(255, 255, 255, 0.95)'};
      font-weight: 600;
      margin-bottom: 0.5rem;
      display: block;
    }

    .events-container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1.5rem;
    }

    .event-card {
      border-radius: ${style.includes('brutalist') ? '0' : '20px'};
      padding: 1.75rem;
      transition: all 0.3s ease;
      animation: fadeIn 0.6s ease backwards;
    }

    .event-card h3 {
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#000000' : '#ffffff'};
      font-size: 1.375rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
      line-height: 1.3;
    }

    .event-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .event-badge {
      background: rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      padding: 0.375rem 0.875rem;
      border-radius: ${style.includes('brutalist') ? '0' : '20px'};
      font-size: 0.8125rem;
      font-weight: 600;
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#000000' : '#ffffff'};
      border: 1px solid rgba(255, 255, 255, 0.25);
    }

    .event-description {
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#333333' : 'rgba(255, 255, 255, 0.85)'};
      line-height: 1.6;
      margin-bottom: 1rem;
      font-size: 0.9375rem;
    }

    .event-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.15);
    }

    .event-price {
      font-size: 1.125rem;
      font-weight: 700;
      color: ${style.includes('cyberpunk') || style.includes('neon') ? '#00d4ff' : '#ffd700'};
    }

    .event-location {
      color: ${style.includes('brutalist') && style !== 'monochrome' ? '#666666' : 'rgba(255, 255, 255, 0.8)'};
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .page-header h1 {
        font-size: 2rem;
      }
      
      .filters-grid {
        grid-template-columns: 1fr;
      }
      
      .events-container {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body data-ai="antigravity">
  <!-- Navigation -->
  <nav class="template-nav">
    <button class="nav-prev" onclick="navigateTemplate(-1)" aria-label="Previous template">←</button>
    <span class="template-indicator">Template ${num}/50</span>
    <button class="nav-next" onclick="navigateTemplate(1)" aria-label="Next template">→</button>
  </nav>

  <div class="main-container">
    <!-- Header -->
    <header class="page-header">
      <h1>Toronto Events</h1>
      <p>${theme}</p>
    </header>

    <!-- Filters -->
    <div class="filters-container">
      <div class="filters-grid">
        <div class="filter-group">
          <label for="search-filter">Search Events</label>
          <input type="text" id="search-filter" placeholder="Search...">
        </div>
        <div class="filter-group">
          <label for="category-filter">Category</label>
          <select id="category-filter">
            <option value="all">All Categories</option>
            <option value="music">Music</option>
            <option value="art">Art</option>
            <option value="food">Food & Drink</option>
            <option value="sports">Sports</option>
            <option value="tech">Tech</option>
            <option value="networking">Networking</option>
          </select>
        </div>
        <div class="filter-group">
          <label for="date-filter">Date Range</label>
          <select id="date-filter">
            <option value="all">All Dates</option>
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>
        </div>
        <div class="filter-group">
          <label for="price-filter">Price</label>
          <select id="price-filter">
            <option value="all">All Prices</option>
            <option value="free">Free</option>
            <option value="paid">Paid</option>
            <option value="under20">Under $20</option>
            <option value="under50">Under $50</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Events Grid -->
    <div class="events-container" id="events-grid">
      <!-- Events will be populated by JavaScript -->
    </div>
  </div>

  <script src="blog_template_base.js"></script>
  <script>
    // Powered by antigravity
    const blogEngine = new BlogTemplateEngine(${num});
    
    // Custom event card rendering for this template
    blogEngine.renderEventCard = function(event) {
      return \`
        <div class="event-card" data-category="\${event.category || 'general'}">
          <h3>\${event.title || 'Untitled Event'}</h3>
          <div class="event-meta">
            <span class="event-badge">📅 \${this.formatDate(event.date)}</span>
            \${event.category ? \`<span class="event-badge">🏷️ \${event.category}</span>\` : ''}
          </div>
          <p class="event-description">\${event.description || 'No description available.'}</p>
          <div class="event-footer">
            <span class="event-price">\${this.formatPrice(event.price)}</span>
            <span class="event-location">📍 \${event.location || 'TBA'}</span>
          </div>
        </div>
      \`;
    };
    
    // Initialize
    blogEngine.init();
  </script>
</body>
</html>`;
}

// Generate all templates
console.log('🚀 Generating 50 blog templates...\n');

templates.forEach(config => {
    const html = generateTemplate(config);
    const filename = `blog${config.num}.html`;
    const filepath = path.join(__dirname, filename);

    fs.writeFileSync(filepath, html, 'utf8');
    console.log(`✅ Created ${filename} - ${config.theme}`);
});

console.log('\n🎉 All 50 templates generated successfully!');
console.log('📝 Each template includes:');
console.log('   - Unique visual theme');
console.log('   - Full event filtering functionality');
console.log('   - Navigation arrows (prev/next)');
console.log('   - Hidden "antigravity" signatures');
console.log('   - Responsive design');
