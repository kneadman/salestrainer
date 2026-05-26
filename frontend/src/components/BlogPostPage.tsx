import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getBlogPostPublic, type BlogPostDetailDTO } from "../api";

export function BlogPostPage() {
  /** Display a single published blog post. */
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<BlogPostDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setError(false);
    getBlogPostPublic(slug)
      .then((res) => setPost(res))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="min-h-screen bg-navy-900">
      <header className="border-b border-white/[0.05] bg-navy-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <a href="/" className="text-white font-bold text-lg" onClick={(e) => { if (e.button === 0 && !e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); window.location.href = "/"; } }}>
            Тренажер для менеджеров
          </a>
          <a
            href="/blog"
            className="text-sm text-text-secondary hover:text-white transition-colors"
            onClick={(e) => { if (e.button === 0 && !e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); window.location.href = "/blog"; } }}
          >
            Блог
          </a>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {loading ? (
          <div className="animate-pulse space-y-6">
            <div className="aspect-video bg-navy-700 rounded-2xl" />
            <div className="h-8 bg-navy-700 rounded w-2/3" />
            <div className="h-4 bg-navy-700 rounded w-1/3" />
            <div className="space-y-3">
              <div className="h-4 bg-navy-700 rounded w-full" />
              <div className="h-4 bg-navy-700 rounded w-full" />
              <div className="h-4 bg-navy-700 rounded w-5/6" />
            </div>
          </div>
        ) : error || !post ? (
          <div className="text-center py-20">
            <h1 className="text-2xl font-bold text-white mb-3">Статья не найдена</h1>
            <p className="text-text-secondary mb-6">Возможно, она была удалена или ещё не опубликована.</p>
            <a
              href="/blog"
              className="inline-flex items-center px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white font-medium transition-colors"
              onClick={(e) => { if (e.button === 0 && !e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); window.location.href = "/blog"; } }}
            >
              Все статьи
            </a>
          </div>
        ) : (
          <article>
            {post.cover_image_url ? (
              <div className="aspect-video rounded-2xl overflow-hidden mb-8">
                <img src={post.cover_image_url} alt={post.title} className="w-full h-full object-cover" />
              </div>
            ) : null}
            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-4">{post.title}</h1>
            <div className="flex items-center gap-3 text-sm text-text-tertiary mb-10">
              <span>{post.author_name}</span>
              <span>·</span>
              <span>{post.published_at ? new Date(post.published_at).toLocaleDateString("ru-RU") : ""}</span>
            </div>
            <div className="prose prose-invert max-w-none whitespace-pre-wrap text-text-secondary leading-relaxed">
              {post.content}
            </div>
          </article>
        )}
      </main>
    </div>
  );
}
