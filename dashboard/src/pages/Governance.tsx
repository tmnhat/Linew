import { useState, useEffect } from 'react';
import { articlesApi, Article } from '../services/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import clsx from 'clsx';

const STATE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  WRITTEN: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Đã viết' },
  GOVERNED: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Đã kiểm duyệt' },
  APPROVED: { bg: 'bg-green-100', text: 'text-green-800', label: 'Đã duyệt' },
  REJECTED: { bg: 'bg-red-100', text: 'text-red-800', label: 'Từ chối' },
  PUBLISHED: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'Đã đăng' },
};

export default function Governance() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<'pending' | 'approved' | 'rejected' | 'published'>('pending');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadArticles = async () => {
    setLoading(true);
    try {
      let states: string;
      switch (filter) {
        case 'pending':
          states = 'WRITTEN,GOVERNED';
          break;
        case 'approved':
          states = 'APPROVED';
          break;
        case 'rejected':
          states = 'REJECTED';
          break;
        case 'published':
          states = 'PUBLISHED';
          break;
      }
      const data = await articlesApi.list({ state: states, page, limit: 20 });
      setArticles(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Failed to load articles:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArticles();
  }, [filter, page]);

  const handleApprove = async (id: string) => {
    setActionLoading(true);
    try {
      await articlesApi.approve(id);
      loadArticles();
    } catch (error) {
      console.error('Approve failed:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    const reason = prompt('Lý do từ chối:');
    if (!reason) return;
    setActionLoading(true);
    try {
      await articlesApi.reject(id, reason);
      loadArticles();
    } catch (error) {
      console.error('Reject failed:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnpublish = async (id: string) => {
    if (!confirm('Hủy đăng bài viết này?')) return;
    setActionLoading(true);
    try {
      await articlesApi.unpublish(id);
      loadArticles();
    } catch (error) {
      console.error('Unpublish failed:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRepublish = async (id: string) => {
    setActionLoading(true);
    try {
      await articlesApi.republish(id);
      loadArticles();
    } catch (error) {
      console.error('Republish failed:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Kiểm duyệt</h1>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="flex border-b">
          {(['pending', 'approved', 'rejected', 'published'] as const).map((f) => (
            <button
              key={f}
              onClick={() => {
                setFilter(f);
                setPage(1);
              }}
              className={clsx(
                'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                filter === f
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {f === 'pending' ? 'Chờ duyệt' :
               f === 'approved' ? 'Đã duyệt' :
               f === 'rejected' ? 'Từ chối' : 'Đã đăng'}
            </button>
          ))}
        </div>

        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Đang tải...</div>
          ) : articles.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Không có bài viết nào
            </div>
          ) : (
            articles.map((article) => (
              <div key={article.id} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-gray-900 truncate">
                        {article.original_title || 'Untitled'}
                      </h3>
                      {article.category && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">
                          {article.category}
                        </span>
                      )}
                      <span
                        className={clsx(
                          'text-xs px-2 py-0.5 rounded',
                          STATE_STYLES[article.state]?.bg,
                          STATE_STYLES[article.state]?.text
                        )}
                      >
                        {STATE_STYLES[article.state]?.label || article.state}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 line-clamp-2">
                      {article.original_summary || article.body_html?.replace(/<[^>]*>/g, '').substring(0, 200)}
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                      <span>
                        {article.word_count || 0} từ
                      </span>
                      {article.trend_score !== undefined && (
                        <span>Trend: {article.trend_score}</span>
                      )}
                      {article.category_confidence !== undefined && (
                        <span>Confidence: {(article.category_confidence * 100).toFixed(0)}%</span>
                      )}
                      <span>
                        {formatDistanceToNow(new Date(article.created_at), {
                          addSuffix: true,
                          locale: vi,
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => setSelectedArticle(article)}
                      className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded border"
                    >
                      👁️ Xem
                    </button>
                    {filter === 'pending' && (
                      <>
                        <button
                          onClick={() => handleApprove(article.id)}
                          disabled={actionLoading}
                          className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
                        >
                          ✅ Duyệt
                        </button>
                        <button
                          onClick={() => handleReject(article.id)}
                          disabled={actionLoading}
                          className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
                        >
                          ❌ Từ chối
                        </button>
                      </>
                    )}
                    {filter === 'published' && (
                      <>
                        <button
                          onClick={() => handleUnpublish(article.id)}
                          disabled={actionLoading}
                          className="px-3 py-1 text-sm bg-orange-600 hover:bg-orange-700 text-white rounded disabled:opacity-50"
                        >
                          📤 Hủy đăng
                        </button>
                        <button
                          onClick={() => handleRepublish(article.id)}
                          disabled={actionLoading}
                          className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50"
                        >
                          🔄 Đăng lại
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              ← Trang trước
            </button>
            <span className="text-sm text-gray-600">
              Trang {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Trang sau →
            </button>
          </div>
        )}
      </div>

      {/* Article Detail Modal */}
      {selectedArticle && (
        <ArticleModal
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  );
}

function ArticleModal({
  article,
  onClose,
  onApprove,
  onReject,
}: {
  article: Article;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const isPending = article.state === 'WRITTEN' || article.state === 'GOVERNED';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Chi tiết bài viết</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              {article.original_title || 'Untitled'}
            </h3>
            <div className="flex items-center gap-2 flex-wrap">
              {article.category && (
                <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                  {article.category}
                </span>
              )}
              {article.tags?.map((tag) => (
                <span key={tag} className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                  #{tag}
                </span>
              ))}
            </div>
          </div>

          {article.original_summary && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Tóm tắt gốc</h4>
              <p className="text-sm text-gray-600">{article.original_summary}</p>
            </div>
          )}

          {article.meta_title && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Meta Title</h4>
              <p className="text-sm text-gray-900">{article.meta_title}</p>
            </div>
          )}

          {article.meta_description && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Meta Description</h4>
              <p className="text-sm text-gray-600">{article.meta_description}</p>
            </div>
          )}

          {article.body_html && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Nội dung</h4>
              <div
                className="text-sm text-gray-700 prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: article.body_html }}
              />
            </div>
          )}

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Số từ</span>
              <div className="font-medium">{article.word_count || 0}</div>
            </div>
            <div>
              <span className="text-gray-500">Điểm xu hướng</span>
              <div className="font-medium">{article.trend_score?.toFixed(2) || '-'}</div>
            </div>
            <div>
              <span className="text-gray-500">Độ confidence</span>
              <div className="font-medium">
                {article.category_confidence ? `${(article.category_confidence * 100).toFixed(0)}%` : '-'}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Chế độ</span>
              <div className="font-medium">{article.mode}</div>
            </div>
            <div>
              <span className="text-gray-500">Priority</span>
              <div className="font-medium">{article.priority}</div>
            </div>
            <div>
              <span className="text-gray-500">URL gốc</span>
              <a
                href={article.original_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline text-xs"
              >
                Mở link
              </a>
            </div>
          </div>

          {article.wp_url && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">WordPress URL</h4>
              <a
                href={article.wp_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline text-sm"
              >
                {article.wp_url}
              </a>
            </div>
          )}
        </div>

        {isPending && (
          <div className="p-4 border-t flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Đóng
            </button>
            <button
              onClick={() => {
                onReject(article.id);
                onClose();
              }}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              ❌ Từ chối
            </button>
            <button
              onClick={() => {
                onApprove(article.id);
                onClose();
              }}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
            >
              ✅ Duyệt đăng
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
