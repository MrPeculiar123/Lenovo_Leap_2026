import { ExternalLink, BookOpen, Clock3 } from 'lucide-react';

function isOpenableUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value);
}

export default function ResourceList({ resources = [], title = 'Grounded resources' }) {
  const visibleResources = resources.filter((resource) => resource?.title);
  if (!visibleResources.length) return null;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2">
        <BookOpen size={18} className="text-indigo-600" />
        <h2 className="font-bold text-slate-900">{title}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {visibleResources.map((resource) => (
          <article key={resource.id || `${resource.title}-${resource.url_or_ref}`} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-semibold text-slate-800">{resource.title}</h3>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                  {resource.resource_type || 'resource'}{resource.difficulty ? ` · ${resource.difficulty}` : ''}
                </p>
              </div>
              {isOpenableUrl(resource.url_or_ref) ? (
                <a
                  href={resource.url_or_ref}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
                >
                  Open <ExternalLink size={14} />
                </a>
              ) : (
                <span className="shrink-0 text-xs text-slate-400">Reference only</span>
              )}
            </div>
            {resource.content_snippet && <p className="mt-3 text-sm leading-6 text-slate-600">{resource.content_snippet}</p>}
            {resource.estimated_minutes && (
              <p className="mt-3 inline-flex items-center gap-1 text-xs text-slate-500"><Clock3 size={13} /> {resource.estimated_minutes} min</p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
