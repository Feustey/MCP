# Configuration Cloudflare pour api.dazno.de

## 1. Page Rules
- URL: api.dazno.de/docs*
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 hour
  - Browser Cache TTL: 30 minutes

- URL: api.dazno.de/api/*
  - Cache Level: Bypass
  - Security Level: High

## 2. Performance Settings
- Auto Minify: ON (JavaScript, CSS, HTML)
- Brotli: ON
- HTTP/2: ON
- HTTP/3 (with QUIC): ON
- 0-RTT Connection Resumption: ON

## 3. Caching
- Browser Cache TTL: 4 hours
- Always Online: ON
- Development Mode: OFF

## 4. Network
- WebSockets: ON
- IP Geolocation: ON
- Maximum Upload Size: 100MB

## 5. Speed > Optimization
- Image Resizing: ON
- Polish: Lossless
- WebP: ON
