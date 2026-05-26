import { useEffect, useState } from "react";
import { listBlogPostsPublic, type BlogPostPublicDTO } from "../api";

export function BlogListPage() {
  /** Public blog listing with load-more pagination. */
  const [posts, setPosts] = useState<BlogPostPublicDTO[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = async (nextOffset: number, append: boolean) => {
    if (nextOffset === 0) setLoading(true);
    else setLoadingMore(true);
    try {
      const res = await listBlogPostsPublic(9, nextOffset);
      setPosts((prev) => (append ? [...prev, ...res.items] : res.items));
      setTotal(res.total);
      setOffset(nextOffset + res.items.length);
    } catch {
      // silently ignore on public page
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    void load(0, false);
  }, []);

  const hasMore = posts.length < total;

  return (
    <div className="min-h-screen bg-navy-900">
      <header className="border-b border-white/[0.05] bg-navy-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <a href="/" className="text-white font-bold text-lg" onClick={(e) => { if (e.button === 0 && !e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); window.location.href = "/"; } }}>
            Тренажер для менеджеров
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-10">Блог</h1>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-navy-800/40 rounded-2xl overflow-hidden border border-white/[0.05] animate-pulse">
                <div className="aspect-video bg-navy-700" />
                <div className="p-5 space-y-3">
                  <div className="h-5 bg-navy-700 rounded w-3/4" />
                  <div className="h-4 bg-navy-700 rounded w-full" />
                  <div className="h-4 bg-navy-700 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : posts.length === 0 ? (
          <p className="text-text-secondary text-center py-20">Пока нет опубликованных статей.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {posts.map((post) => (
                <a
                  key={post.id}
                  href={`/blog/${post.slug}`}
                  className="group block bg-navy-800/60 rounded-2xl overflow-hidden border border-white/[0.05] hover:border-white/10 transition-colors"
                  onClick={(e) => {
                    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
                    e.preventDefault();
                    window.location.href = `/blog/${post.slug}`;
                  }}
                >
                  <div className="aspect-video bg-navy-700 overflow-hidden">
                    {post.cover_image_url ? (
                      <img
                        src={post.cover_image_url}
                        alt={post.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-navy-600 to-navy-700" />
                    )}
                  </div>
                  <div className="p-5">
                    <h2 className="text-white font-semibold text-lg line-clamp-2 group-hover:text-accent-teal transition-colors">
                      {post.title}
                    </h2>
                    <p className="text-text-secondary text-sm mt-2 line-clamp-3">{post.excerpt}</p>
                    <div className="flex items-center justify-between mt-4 text-xs text-text-tertiary">
                      <span>{post.author_name}</span>
                      <span>{post.published_at ? new Date(post.published_at).toLocaleDateString("ru-RU") : ""}</span>
                    </div>
                  </div>
                </a>
              ))}
            </div>

            {hasMore ? (
              <div className="text-center mt-10">
                <button
                  type="button"
                  onClick={() => void load(offset, true)}
                  disabled={loadingMore}
                  className="inline-flex items-center px-6 py-3 bg-white/5 hover:bg-white/10 disabled:opacity-50 border border-white/10 rounded-xl text-white font-medium transition-colors"
                >
                  {loadingMore ? "Загрузка..." : "Показать ещё"}
                </button>
              </div>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
