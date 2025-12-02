# PIA Request Automation System - Frontend

Modern React frontend for the Privacy Impact Assessment Request Automation System.

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Data fetching and caching
- **React Router** - Client-side routing
- **Zustand** - State management
- **Axios** - HTTP client
- **Vite** - Build tool and dev server
- **Heroicons** - Icon library

## Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

## Installation

```bash
# Install dependencies
npm install
```

## Development

```bash
# Start development server (http://localhost:3000)
npm run dev

# Run linter
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── RequestCard.tsx
│   │   ├── DocumentTable.tsx
│   │   ├── WorkflowProgress.tsx
│   │   ├── DeadlineIndicator.tsx
│   │   ├── ClassificationBadge.tsx
│   │   └── StatsCard.tsx
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useRequests.ts
│   │   ├── useDocuments.ts
│   │   ├── useWorkflow.ts
│   │   └── useDashboard.ts
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx
│   │   ├── RequestList.tsx
│   │   ├── RequestDetail.tsx
│   │   ├── NewRequest.tsx
│   │   └── Login.tsx
│   ├── services/           # API service layer
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── requests.ts
│   │   ├── documents.ts
│   │   ├── workflow.ts
│   │   └── dashboard.ts
│   ├── App.tsx             # Main app component
│   ├── index.tsx           # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── Dockerfile              # Production container
├── nginx.conf             # Nginx configuration
└── package.json           # Dependencies and scripts
```

## Features

### Authentication
- Secure login with JWT tokens
- Protected routes
- Automatic token refresh
- Session persistence

### Dashboard
- Real-time metrics and statistics
- Urgent items tracking
- Recent activity feed
- Quick action shortcuts

### Request Management
- Create new PIA requests
- List and filter requests
- View detailed request information
- Track workflow progress
- Monitor deadlines

### Document Handling
- Upload documents
- Automatic classification
- Status tracking
- Document download

### Workflow Tracking
- Visual progress indicators
- Stage-based workflow
- Task management
- Completion estimates

## Component Architecture

### Layout Components
- **Layout**: Main application shell with sidebar and header
- **Sidebar**: Navigation menu with active state
- **Protected Routes**: Authentication guards

### Feature Components
- **RequestCard**: Summary card for request listings
- **DocumentTable**: Tabular view of documents with actions
- **WorkflowProgress**: Visual progress tracking
- **StatsCard**: Metric display cards
- **DeadlineIndicator**: Color-coded deadline badges
- **ClassificationBadge**: Security classification labels

### State Management
- **Zustand** for authentication state
- **React Query** for server state and caching
- **React Router** for URL state

## API Integration

The frontend communicates with the backend API at `http://localhost:8000/api/v1`.

### Endpoints Used
- `POST /auth/login` - User authentication
- `GET /auth/me` - Current user info
- `GET /requests` - List requests
- `POST /requests` - Create request
- `GET /requests/{id}` - Request details
- `POST /requests/{id}/start-processing` - Start automation
- `GET /documents` - List documents
- `POST /documents` - Upload document
- `POST /documents/{id}/classify` - Classify document
- `GET /workflow/tasks` - Workflow tasks
- `GET /workflow/status` - Workflow status
- `GET /dashboard/overview` - Dashboard metrics
- `GET /dashboard/urgent-items` - Urgent items

## Styling

### Tailwind CSS Configuration
- Custom color palette (blue/gray scheme)
- Responsive breakpoints
- Utility classes for rapid development
- Custom scrollbar styles

### Design Principles
- Professional government-appropriate aesthetic
- Clean, minimalist interface
- Accessible color contrasts
- Mobile-first responsive design
- Consistent spacing and typography

## Docker Deployment

```bash
# Build production image
docker build -t pia-frontend .

# Run container
docker run -p 80:80 pia-frontend
```

The Docker build uses a multi-stage process:
1. Build stage: Compiles TypeScript and bundles with Vite
2. Production stage: Serves static files with Nginx

## Environment Variables

Create a `.env` file for environment-specific settings:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Performance Optimizations

- Code splitting with React.lazy
- Asset caching with Nginx
- Gzip compression
- React Query caching
- Optimistic updates
- Debounced search inputs

## Accessibility

- Semantic HTML elements
- ARIA labels and roles
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## Contributing

1. Follow the existing code style
2. Use TypeScript for type safety
3. Write semantic, accessible HTML
4. Test on multiple screen sizes
5. Ensure all links and navigation work

## License

Proprietary - Government Use Only
