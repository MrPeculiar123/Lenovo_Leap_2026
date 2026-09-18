export function Loading({ fullScreen = true, message = 'Loading...' }) {
  const content = (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className="relative w-12 h-12">
        <div className="absolute top-0 left-0 w-full h-full border-4 border-indigo-500/20 rounded-full"></div>
        <div className="absolute top-0 left-0 w-full h-full border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
      <p className="text-slate-400 text-sm font-medium tracking-wide animate-pulse">{message}</p>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        {content}
      </div>
    );
  }

  return content;
}
export default Loading;
