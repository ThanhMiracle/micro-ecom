export function ProductGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="candy-card p-5">
          <div className="space-y-2 w-full">
            <div className="skeleton h-5 w-2/3" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-4/5" />
          </div>
          <div className="mt-4 skeleton h-10 w-full" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div className="mt-4 space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="candy-card p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-2 w-full">
              <div className="skeleton h-4 w-1/2" />
              <div className="skeleton h-3 w-3/4" />
            </div>
            <div className="skeleton h-9 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}
