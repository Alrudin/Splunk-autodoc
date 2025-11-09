# Public Directory

This directory contains static assets that are served directly without processing by Vite.

## Contents

- **favicon.svg** - Application favicon (SVG format for modern browsers)
- **robots.txt** - Search engine crawling rules
- **.gitkeep** - Ensures directory is tracked by Git

## Usage

Files placed in this directory are:
- Copied as-is to the build output (`dist/`) during `npm run build`
- Served from the root path (e.g., `/favicon.svg`)
- Not processed by Vite's build pipeline

## Adding Assets

Add additional static assets here as needed:
- `manifest.json` - PWA manifest
- `apple-touch-icon.png` - iOS home screen icon
- `logo192.png`, `logo512.png` - App icons
- `sitemap.xml` - Site structure for search engines
