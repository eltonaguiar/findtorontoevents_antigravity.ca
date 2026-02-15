const https = require('https');
const fs = require('fs');

const events = JSON.parse(fs.readFileSync('next/events.json', 'utf8'));
const aeEvents = events.filter(function(e) { return e.url && e.url.indexOf('allevents.in') >= 0; });

// Sample 15 random AllEvents.in URLs
var sample = [];
var indices = [];
while (sample.length < 15 && indices.length < aeEvents.length) {
  var idx = Math.floor(Math.random() * aeEvents.length);
  if (indices.indexOf(idx) === -1) {
    indices.push(idx);
    sample.push(aeEvents[idx].url);
  }
}

console.log('Testing', sample.length, 'AllEvents.in URLs against resolve API...\n');

var postData = JSON.stringify({ urls: sample });
var opts = {
  hostname: 'findtorontoevents.ca',
  path: '/api/events/resolve_link.php',
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) }
};

var req = https.request(opts, function(res) {
  var d = '';
  res.on('data', function(c) { d += c; });
  res.on('end', function() {
    try {
      var j = JSON.parse(d);
      console.log('Resolved:', j.resolved_count, 'of', j.total, '(' + Math.round(j.resolved_count / j.total * 100) + '% success rate)\n');

      var sources = {};
      j.results.forEach(function(r) {
        var src = r.source || 'Not Found';
        sources[src] = (sources[src] || 0) + 1;
        var status = r.resolved_url ? 'OK' : 'MISS';
        var url = r.resolved_url ? r.resolved_url.substring(0, 70) : (r.error || 'no match');
        console.log('  [' + status + '] ' + r.source + ' via ' + (r.method || '-') + ' -> ' + url);
      });

      console.log('\nBreakdown by source:');
      Object.keys(sources).forEach(function(s) {
        console.log('  ' + s + ': ' + sources[s]);
      });
    } catch (e) {
      console.log('Parse error:', d.substring(0, 500));
    }
  });
});
req.write(postData);
req.end();
