import { useEffect, useState } from "react";
import { listBlogPostsPublic, type BlogPostPublicDTO } from "../api";

export function LatestPostsSection() {
  /** Show the 3 latest published blog posts on the landing page. */
  const [posts, setPosts] = useState<BlogPostPublicDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listBlogPostsPublic(3, 0)
      .then((res) => setPosts(res.items))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading || posts.length === 0) {
    return null;
  }

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-navy-900/50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-accent-teal text-sm font-medium tracking-wider uppercase">Блог</span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">Последние статьи</h2>
        </div>
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
                <h3 className="text-white font-semibold text-lg line-clamp-2 group-hover:text-accent-teal transition-colors">
                  {post.title}
                </h3>
                <p className="text-text-secondary text-sm mt-2 line-clamp-3">{post.excerpt}</p>
                <span className="inline-flex items-center text-accent-teal text-sm font-medium mt-4 group-hover:underline">
                  Читать
                  <svg className="ml-1 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </span>
              </div>
            </a>
          ))}
        </div>
        <div className="text-center mt-10">
          <a
            href="/blog"
            className="inline-flex items-center px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white font-medium transition-colors"
            onClick={(e) => {
              if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
              e.preventDefault();
              window.location.href = "/blog";
            }}
          >
            Все статьи
            <svg className="ml-2 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </div>
      </div>
    </section>
  );
}
