const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, '..', 'company logo.jpg');
const dest = path.join(__dirname, 'public', 'curl-stack-logo.jpg');

try {
  fs.copyFileSync(src, dest);
  console.log('Logo copied successfully to public/curl-stack-logo.jpg');
} catch (err) {
  console.error('Failed to copy logo:', err.message);
  console.log('Please manually copy "company logo.jpg" to "Frontend/public/curl-stack-logo.jpg"');
}
