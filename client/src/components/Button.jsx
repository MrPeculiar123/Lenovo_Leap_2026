import React from 'react';
import { Loader2 } from 'lucide-react';

export function Button({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  className = '',
  onClick,
  icon: Icon = null,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100';

  const variants = {
    primary: 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 focus:ring-indigo-500 border border-indigo-500/30 hover:scale-[1.01] active:scale-[0.99]',
    secondary: 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/80 focus:ring-slate-500 hover:text-white',
    outline: 'bg-transparent hover:bg-slate-900 text-slate-300 hover:text-white border border-slate-700 focus:ring-slate-500',
    ghost: 'bg-transparent hover:bg-slate-900 text-slate-400 hover:text-white focus:ring-slate-500',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3.5 text-base font-semibold',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 mr-2 animate-spin text-current" />
          <span>Processing...</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4 mr-2 text-current" />}
          {children}
        </>
      )}
    </button>
  );
}

export default Button;
