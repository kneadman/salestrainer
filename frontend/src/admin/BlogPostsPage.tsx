import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { createBlogPost, deleteBlogPost, listBlogPosts, updateBlogPost, uploadBlogImage } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { BlogPostDTO } from "./types";
import { formatDate } from "./utils";
import { getErrorMessage } from "../errorMessage";

type BlogPostsPageProps = {
  onNavigate: (path: string) => void;
};

type BlogPostForm = {
  id?: string;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  cover_image_url: string;
  author_name: string;
  is_published: boolean;
};

function emptyForm(): BlogPostForm {
  return {
    title: "",
    slug: "",
    excerpt: "",
    content: "",
    cover_image_url: "",
    author_name: "",
    is_published: false,
  };
}

export function BlogPostsPage(_props: BlogPostsPageProps) {
  /** Manage blog posts: list, search, create, edit, publish toggle, delete. */
  const [posts, setPosts] = useState<BlogPostDTO[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<BlogPostForm>(emptyForm());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPosts(await listBlogPosts(search.trim() || undefined));
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (searchTimer.current) {
      clearTimeout(searchTimer.current);
    }
    searchTimer.current = setTimeout(() => {
      void load();
    }, 300);
    return () => {
      if (searchTimer.current) {
        clearTimeout(searchTimer.current);
      }
    };
  }, [search, load]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        title: form.title,
        slug: form.slug || undefined,
        excerpt: form.excerpt,
        content: form.content,
        cover_image_url: form.cover_image_url || null,
        author_name: form.author_name,
        is_published: form.is_published,
      };
      if (form.id) {
        await updateBlogPost(form.id, payload);
        setSuccess("Статья обновлена.");
      } else {
        await createBlogPost(payload);
        setSuccess("Статья создана.");
      }
      setForm(emptyForm());
      await load();
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (post: BlogPostDTO) => {
    if (!window.confirm("Статья будет удалена безвозвратно. Продолжить?")) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await deleteBlogPost(post.id);
      setSuccess("Статья удалена.");
      await load();
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    }
  };

  const handleImageUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadBlogImage(file);
      setForm((prev) => ({ ...prev, cover_image_url: result.url }));
    } catch (uploadError) {
      setError(getErrorMessage(uploadError));
    } finally {
      setUploading(false);
    }
  };

  if (loading && posts.length === 0) {
    return <LoadingState title="Загрузка статей" />;
  }

  if (error && posts.length === 0) {
    return <ErrorState title="Статьи недоступны" detail={error} />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Контент</span>
          <h1>Статьи блога</h1>
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}

      <section className="admin-panel">
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="admin-form__row">
            <label>
              <span>Заголовок</span>
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
                maxLength={300}
              />
            </label>
            <label>
              <span>Слаг</span>
              <input
                value={form.slug}
                pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                title="Используйте латиницу в нижнем регистре, цифры и дефисы."
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
                placeholder="Автоматически из заголовка"
              />
            </label>
          </div>
          <div className="admin-form__row">
            <label>
              <span>Автор</span>
              <input
                value={form.author_name}
                onChange={(e) => setForm({ ...form, author_name: e.target.value })}
                required
                maxLength={160}
              />
            </label>
            <label className="admin-checkbox">
              <input
                type="checkbox"
                checked={form.is_published}
                onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
              />
              <span>Опубликована</span>
            </label>
          </div>
          <label>
            <span>Краткое описание</span>
            <textarea
              value={form.excerpt}
              onChange={(e) => setForm({ ...form, excerpt: e.target.value })}
              required
              maxLength={1000}
              rows={3}
            />
          </label>
          <label>
            <span>Содержание</span>
            <textarea
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              required
              maxLength={50000}
              rows={8}
            />
          </label>
          <div className="admin-form__row">
            <label>
              <span>Обложка</span>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleImageUpload(file);
                }}
                disabled={uploading}
              />
              <small>Рекомендуемое соотношение 16:9, не более 5 МБ.</small>
            </label>
            {form.cover_image_url ? (
              <div className="admin-image-preview">
                <img src={form.cover_image_url} alt="Обложка" style={{ maxHeight: 120, aspectRatio: "16/9", objectFit: "cover" }} />
              </div>
            ) : null}
          </div>
          <div className="admin-form__actions">
            <button type="submit" className="admin-button admin-button--primary" disabled={saving || uploading}>
              {form.id ? "Сохранить" : "Создать"}
            </button>
            {form.id ? (
              <button type="button" className="admin-button" onClick={() => setForm(emptyForm())}>
                Отмена
              </button>
            ) : null}
          </div>
        </form>
      </section>

      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Список статей</h2>
          <input
            className="admin-search"
            placeholder="Поиск по названию, слагу или содержанию"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {posts.length === 0 ? (
          <EmptyState title="Статей нет" detail="Создайте первую статью, чтобы она появилась на сайте." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Заголовок</th>
                  <th>Автор</th>
                  <th>Статус</th>
                  <th>Обновлено</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post) => (
                  <tr key={post.id}>
                    <td>{post.title}</td>
                    <td>{post.author_name}</td>
                    <td>
                      <Badge tone={post.is_published ? "good" : "neutral"}>
                        {post.is_published ? "Опубликована" : "Черновик"}
                      </Badge>
                    </td>
                    <td>{formatDate(post.updated_at)}</td>
                    <td>
                      <div className="admin-row-actions">
                        <button
                          type="button"
                          className="admin-link-button"
                          onClick={() =>
                            setForm({
                              id: post.id,
                              title: post.title,
                              slug: post.slug,
                              excerpt: post.excerpt,
                              content: "",
                              cover_image_url: post.cover_image_url || "",
                              author_name: post.author_name,
                              is_published: post.is_published,
                            })
                          }
                        >
                          Редактировать
                        </button>
                        <button type="button" className="admin-link-button" onClick={() => void handleDelete(post)}>
                          Удалить
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
