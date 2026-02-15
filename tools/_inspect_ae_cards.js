const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
  await p.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(6000);

  const info = await p.evaluate(function() {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var aeCards = [];

    for (var i = 0; i < cards.length && aeCards.length < 5; i++) {
      var links = cards[i].querySelectorAll('a[href]');
      for (var j = 0; j < links.length; j++) {
        if (links[j].href.indexOf('allevents.in') >= 0) {
          var title = cards[i].querySelector('h2, h3');
          // Get the whole link element's outer context
          var linkParent = links[j].parentElement;
          aeCards.push({
            title: title ? title.textContent.substring(0, 50) : '(no title)',
            linkText: links[j].textContent.trim().substring(0, 40),
            linkHref: links[j].href.substring(0, 90),
            linkClass: links[j].className.substring(0, 80),
            linkTag: links[j].tagName,
            parentTag: linkParent ? linkParent.tagName : null,
            parentClass: linkParent ? linkParent.className.substring(0, 80) : null,
            allLinks: Array.from(links).map(function(l) {
              return { text: l.textContent.trim().substring(0, 30), href: l.href.substring(0, 70) };
            })
          });
          break;
        }
      }
    }

    // Also find total AE events in RAW data
    var rawAE = 0;
    if (window.__RAW_EVENTS__) {
      rawAE = window.__RAW_EVENTS__.filter(function(e) {
        return e.url && e.url.indexOf('allevents.in') >= 0;
      }).length;
    }

    return { totalCards: cards.length, aeInData: rawAE, aeCardsSampled: aeCards.length, samples: aeCards };
  });

  console.log('Total visible cards:', info.totalCards);
  console.log('AllEvents.in events in data:', info.aeInData);
  console.log('AllEvents.in cards found:', info.aeCardsSampled);
  console.log('\nSample cards:');
  info.samples.forEach(function(s, i) {
    console.log('\n--- Card', i + 1, ':', s.title, '---');
    console.log('  Link text:', JSON.stringify(s.linkText));
    console.log('  Link href:', s.linkHref);
    console.log('  Link class:', s.linkClass);
    console.log('  All links in card:');
    s.allLinks.forEach(function(l) {
      console.log('    ', JSON.stringify(l.text), '->', l.href);
    });
  });

  await b.close();
})();
