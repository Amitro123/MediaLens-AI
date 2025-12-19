# DevLens AI Frontend

React-based frontend for DevLens AI video-to-documentation system.

## Features

- 📤 Drag-and-drop video upload
- 🎯 Multiple documentation modes (Bug Reports, Feature Specs, General Docs)
- 📊 Real-time progress tracking
- 📝 Markdown documentation preview
- 🎨 Modern UI with Tailwind CSS

## Development

### Install Dependencies
```bash
npm install
```

### Start Dev Server
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production
```bash
npm run build
```

## API Integration

The frontend proxies API requests to the backend at `http://localhost:8000`. Make sure the backend server is running before starting the frontend.

## Components

- **App.jsx** - Main application layout
- **UploadForm.jsx** - Video upload and mode selection component

## Styling

Uses Tailwind CSS with Shadcn UI design system for consistent, accessible components.
