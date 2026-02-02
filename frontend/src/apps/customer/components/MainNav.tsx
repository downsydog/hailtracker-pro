import { NavLink } from 'react-router-dom';
import { useAuth } from '../../../contexts/auth-context';
import UserMenu from './UserMenu';

export default function MainNav() {
  const { tenant, canManageTeam, canManageSettings } = useAuth();

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-lg transition ${
      isActive
        ? 'bg-purple-600 text-white'
        : 'text-gray-400 hover:bg-gray-700 hover:text-white'
    }`;

  return (
    <header className="bg-gray-800 border-b border-gray-700">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Logo & Brand */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
            </div>
            <div>
              <span className="text-white font-semibold">HailTracker Pro</span>
              {tenant && (
                <span className="text-gray-400 text-sm ml-2">| {tenant.name}</span>
              )}
            </div>
          </div>

          {/* Main Navigation */}
          <nav className="flex items-center gap-1">
            <NavLink to="/app" end className={navLinkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/app/storms" className={navLinkClass}>
              Storms
            </NavLink>
            <NavLink to="/app/leads" className={navLinkClass}>
              Leads
            </NavLink>
            {canManageTeam && (
              <NavLink to="/app/team" className={navLinkClass}>
                Team
              </NavLink>
            )}
            {canManageSettings && (
              <NavLink to="/app/settings" className={navLinkClass}>
                Settings
              </NavLink>
            )}
          </nav>
        </div>

        {/* User Menu */}
        <UserMenu />
      </div>
    </header>
  );
}
