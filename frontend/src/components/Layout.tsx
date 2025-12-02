import { ReactNode, useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  HomeIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  BellIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import {
  HomeIcon as HomeIconSolid,
  DocumentTextIcon as DocumentTextIconSolid,
  ClipboardDocumentListIcon as ClipboardDocumentListIconSolid,
  ChartBarIcon as ChartBarIconSolid,
} from '@heroicons/react/24/solid';

interface LayoutProps {
  children?: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon, iconActive: HomeIconSolid },
  { name: 'Requests', href: '/requests', icon: ClipboardDocumentListIcon, iconActive: ClipboardDocumentListIconSolid },
  { name: 'Documents', href: '/documents', icon: DocumentTextIcon, iconActive: DocumentTextIconSolid },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon, iconActive: ChartBarIconSolid },
];

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen bg-navy-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          bg-gradient-to-b from-navy-900 via-navy-900 to-navy-950 border-r border-navy-800
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-navy-800">
          <Link to="/" className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-tronas-400 to-tronas-600 flex items-center justify-center shadow-glow">
                <SparklesIcon className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-tronas-400 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Tronas</h1>
              <p className="text-[10px] text-tronas-400 uppercase tracking-wider">PIA Automation</p>
            </div>
          </Link>
          <button
            className="lg:hidden text-navy-400 hover:text-white transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          {navigation.map((item) => {
            const active = isActive(item.href);
            const Icon = active ? item.iconActive : item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
                  ${active
                    ? 'bg-tronas-500/10 text-tronas-400 shadow-inner-glow'
                    : 'text-navy-400 hover:text-white hover:bg-navy-800/50'
                  }
                `}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-tronas-400' : ''}`} />
                <span className="font-medium">{item.name}</span>
                {active && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-tronas-400 shadow-glow" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Quick Stats */}
        <div className="px-4 pb-6">
          <div className="bg-navy-800/50 rounded-xl p-4 border border-navy-700">
            <h3 className="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-3">
              Processing Status
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-navy-300">AI Classification</span>
                  <span className="text-tronas-400 font-medium">87%</span>
                </div>
                <div className="h-1.5 bg-navy-700 rounded-full overflow-hidden">
                  <div className="h-full w-[87%] bg-gradient-to-r from-tronas-500 to-tronas-400 rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-navy-300">Documents</span>
                  <span className="text-tronas-400 font-medium">1,247</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* User Profile */}
        <div className="border-t border-navy-800 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-tronas-500 to-tronas-700 flex items-center justify-center text-white font-semibold shadow-glow">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-navy-400 truncate capitalize">{user?.role || 'Viewer'}</p>
            </div>
            <button
              onClick={logout}
              className="p-2 text-navy-400 hover:text-danger-500 hover:bg-navy-800 rounded-lg transition-colors"
              title="Sign out"
            >
              <ArrowRightOnRectangleIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-navy-900/50 backdrop-blur-xl border-b border-navy-800 flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-4">
            <button
              className="lg:hidden p-2 text-navy-400 hover:text-white hover:bg-navy-800 rounded-lg transition-colors"
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="w-6 h-6" />
            </button>

            {/* Search */}
            <div className="relative hidden sm:block">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-500" />
              <input
                type="text"
                placeholder="Search requests, documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-80 pl-10 pr-4 py-2 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Notifications */}
            <button className="relative p-2 text-navy-400 hover:text-white hover:bg-navy-800 rounded-xl transition-colors">
              <BellIcon className="w-6 h-6" />
              <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-danger-500 rounded-full border-2 border-navy-900" />
            </button>

            {/* Settings */}
            <Link
              to="/settings"
              className="p-2 text-navy-400 hover:text-white hover:bg-navy-800 rounded-xl transition-colors"
            >
              <Cog6ToothIcon className="w-6 h-6" />
            </Link>

            {/* New Request Button */}
            <Link
              to="/requests/new"
              className="hidden sm:flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white font-medium rounded-xl shadow-glow transition-all duration-200"
            >
              <span>New Request</span>
              <span className="text-lg">+</span>
            </Link>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-navy-950 bg-grid-pattern">
          <div className="p-4 lg:p-6 animate-fade-in">
            {children || <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}
