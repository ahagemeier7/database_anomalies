import { NavLink, Outlet } from 'react-router-dom';
import { Shield, Layout as LayoutIcon, ClipboardList } from 'lucide-react';

export function Layout() {
  const linkClasses = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-50 text-indigo-600'
        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
    }`;

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2.5">
                <Shield className="h-6 w-6 text-indigo-600" />
                <span className="text-lg font-bold text-gray-900">FraudOps</span>
              </div>
              <div className="flex items-center gap-1">
                <NavLink to="/" className={linkClasses} end>
                  <LayoutIcon className="h-4 w-4" />
                  Workers
                </NavLink>
                <NavLink to="/revisions" className={linkClasses}>
                  <ClipboardList className="h-4 w-4" />
                  Revisions
                </NavLink>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
