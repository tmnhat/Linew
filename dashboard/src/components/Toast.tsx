import { useEffect } from 'react';
import { useToastStore } from '../store/toast';
import clsx from 'clsx';

export default function Toast() {
  const { toasts, removeToast } = useToastStore();

  useEffect(() => {
    toasts.forEach((toast) => {
      const timeout = setTimeout(() => {
        removeToast(toast.id);
      }, 5000);
      return () => clearTimeout(timeout);
    });
  }, [toasts, removeToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={clsx(
            'min-w-72 p-4 rounded-lg shadow-lg text-white animate-slide-in',
            toast.type === 'success' && 'bg-green-600',
            toast.type === 'error' && 'bg-red-600',
            toast.type === 'warning' && 'bg-yellow-600',
            toast.type === 'info' && 'bg-blue-600'
          )}
        >
          <div className="font-medium">{toast.title}</div>
          <div className="text-sm opacity-90">{toast.message}</div>
        </div>
      ))}
    </div>
  );
}
