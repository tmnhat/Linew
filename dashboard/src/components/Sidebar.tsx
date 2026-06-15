import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import clsx from 'clsx';
import { pipelineApi } from '../services/api';
import { useToastStore } from '../store/toast';
import { useAuthStore } from '../store/auth';

const navItems = [
  { path: '/overview', label: 'Tổng quan', icon: '📊' },
  { path: '/sources', label: 'Nguồn tin', icon: '📡' },
  { path: '/pipeline', label: 'Pipeline', icon: '⚙️' },
  { path: '/governance', label: 'Kiểm duyệt', icon: '🛡️' },
  { path: '/distribution', label: 'Distribution', icon: '📤' },
  { path: '/newsletter', label: 'Newsletter', icon: '📧' },
  { path: '/seo', label: 'SEO Bot', icon: '🔍' },
  { path: '/settings', label: 'Cài đặt', icon: '⚡' },
  { path: '/logs', label: 'Nhật ký', icon: '📋' },
];

export default function Sidebar() {
  const { addToast } = useToastStore();
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const [isRunning, setIsRunning] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/dashboard/login');
  };

  const handleRunPipeline = async (mode: 'normal' | 'allin') => {
    setIsRunning(true);
    try {
      const api = mode === 'allin' ? pipelineApi.runAllin : pipelineApi.run;
      const result = await api({ limit: 10 });
      addToast({
        type: 'success',
        title: `Pipeline ${mode === 'allin' ? 'All-in' : 'Normal'}`,
        message: result.message,
      });
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Pipeline Error',
        message: String(error),
      });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-gray-900 text-white flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-primary-400">Linew</h1>
        <p className="text-xs text-gray-400">AI Media Platform</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'flex items-center px-4 py-3 text-sm transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )
            }
          >
            <span className="mr-3">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Pipeline Controls */}
      <div className="p-4 border-t border-gray-800">
        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wider">
          Pipeline Controls
        </p>
        <div className="space-y-2">
          <button
            onClick={() => handleRunPipeline('normal')}
            disabled={isRunning}
            className={clsx(
              'w-full py-2 px-3 rounded text-sm font-medium transition-colors',
              'bg-primary-600 hover:bg-primary-700 text-white',
              isRunning && 'opacity-50 cursor-not-allowed'
            )}
          >
            ▶ Run Normal
          </button>
          <button
            onClick={() => handleRunPipeline('allin')}
            disabled={isRunning}
            className={clsx(
              'w-full py-2 px-3 rounded text-sm font-medium transition-colors',
              'bg-purple-600 hover:bg-purple-700 text-white',
              isRunning && 'opacity-50 cursor-not-allowed'
            )}
          >
            ⚡ Run All-in
          </button>
        </div>
      </div>

      {/* Logout */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={handleLogout}
          className="w-full py-2 px-3 rounded text-sm font-medium transition-colors bg-gray-800 hover:bg-red-600 text-gray-300 hover:text-white"
        >
          🚪 Đăng xuất
        </button>
      </div>
    </aside>
  );
}
