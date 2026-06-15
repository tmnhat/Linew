import { useState, useEffect, useCallback } from 'react';
import { pipelineApi, sourcesApi } from '../services/api';
import clsx from 'clsx';

const STEPS = [
  { key: 'SIGNAL_COLLECTED', label: 'Signal', description: 'Thu thập tín hiệu từ RSS feeds' },
  { key: 'CATEGORIZED', label: 'Phân loại', description: 'AI phân loại danh mục bài viết' },
  { key: 'TRENDING', label: 'Xu hướng', description: 'Đánh giá điểm xu hướng' },
  { key: 'RESEARCHED', label: 'Nghiên cứu', description: 'Tìm kiếm thông tin bổ sung' },
  { key: 'WRITTEN', label: 'Viết bài', description: 'AI viết nội dung bài viết' },
  { key: 'GOVERNED', label: 'Kiểm duyệt', description: 'Kiểm tra chất lượng nội dung' },
  { key: 'APPROVED', label: 'Duyệt bài', description: 'Duyệt để đăng tải' },
  { key: 'PUBLISHED', label: 'Đã đăng', description: 'Đăng lên WordPress' },
];

const STATE_COLORS: Record<string, string> = {
  SIGNAL_COLLECTED: 'border-blue-500 bg-blue-50',
  CATEGORIZED: 'border-indigo-500 bg-indigo-50',
  TRENDING: 'border-purple-500 bg-purple-50',
  RESEARCHED: 'border-cyan-500 bg-cyan-50',
  WRITTEN: 'border-yellow-500 bg-yellow-50',
  GOVERNED: 'border-orange-500 bg-orange-50',
  APPROVED: 'border-green-500 bg-green-50',
  PUBLISHED: 'border-emerald-500 bg-emerald-50',
  FAILED: 'border-red-500 bg-red-50',
};

interface PipelineInfo {
  state: string;
  mode: string;
  started_at: string | null;
  has_lock: boolean;
  is_running: boolean;
  is_continuous: boolean;
  stats: {
    articles_processed?: number;
    articles_published?: number;
    articles_failed?: number;
    last_updated?: string;
  };
}

interface QueueStatus {
  is_running: boolean;
  mode: string;
  in_progress: number;
  queue_size: number;
  last_run_at: string | null;
  queue_by_state: Record<string, number>;
  running: number;
  failed_articles: Array<{
    id: string;
    original_title: string;
    state: string;
    last_error: string | null;
    retry_count: number;
  }>;
}

export default function Pipeline() {
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [pipelineInfo, setPipelineInfo] = useState<PipelineInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [continuousLoading, setContinuousLoading] = useState(false);
  const [fetchingRSS, setFetchingRSS] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const [queueStatus, info] = await Promise.all([
        pipelineApi.status(),
        pipelineApi.info(),
      ]);
      setStatus(queueStatus);
      setPipelineInfo(info);
      setError(null);
    } catch (err) {
      console.error('Failed to load status:', err);
      setError('Không thể tải trạng thái pipeline');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [loadStatus]);

  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setSuccess(null);
    } else {
      setSuccess(message);
      setError(null);
    }
    setTimeout(() => {
      setError(null);
      setSuccess(null);
    }, 3000);
  };

  const handleRun = async (mode: 'normal' | 'allin') => {
    if (running) return;
    setRunning(true);
    setError(null);
    try {
      const api = mode === 'allin' ? pipelineApi.runAllin : pipelineApi.run;
      await api({ limit: 20 });
      await loadStatus();
      showMessage(`${mode === 'allin' ? 'All-in' : 'Normal'} pipeline đã được kích hoạt`);
    } catch (err: any) {
      console.error('Pipeline run failed:', err);
      showMessage(err.message || 'Pipeline run failed', true);
    } finally {
      setRunning(false);
    }
  };

  const handleStartContinuous = async () => {
    if (continuousLoading) return;
    setContinuousLoading(true);
    setError(null);
    try {
      const result = await pipelineApi.startContinuous({ limit: 10 });
      if (result.success) {
        showMessage('Continuous pipeline đã được khởi động');
        await loadStatus();
      } else {
        showMessage(result.message || 'Không thể khởi động', true);
      }
    } catch (err: any) {
      console.error('Start continuous failed:', err);
      showMessage(err.message || 'Không thể khởi động continuous pipeline', true);
    } finally {
      setContinuousLoading(false);
    }
  };

  const handleStop = async () => {
    setError(null);
    try {
      const result = await pipelineApi.stop();
      if (result.success) {
        showMessage('Pipeline đã được dừng');
        await loadStatus();
      } else {
        showMessage(result.message || 'Không thể dừng', true);
      }
    } catch (err: any) {
      console.error('Stop failed:', err);
      showMessage(err.message || 'Không thể dừng pipeline', true);
    }
  };

  const handleRetry = async (articleId: string) => {
    try {
      await pipelineApi.retry(articleId);
      await loadStatus();
      showMessage('Đã thử lại bài viết');
    } catch (error) {
      console.error('Retry failed:', error);
      showMessage('Không thể thử lại bài viết', true);
    }
  };

  const handleCleanup = async () => {
    if (!confirm('Xóa tất cả các bài viết ở trạng thái FAILED, REJECTED và SKIPPED?\n\nHành động này không thể hoàn tác!')) return;
    try {
      setLoading(true);
      await pipelineApi.cleanupFailed();
      await loadStatus();
      showMessage('Đã dọn dẹp các bài viết thất bại');
    } catch (error) {
      console.error('Cleanup failed:', error);
      showMessage('Không thể dọn dẹp', true);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRSS = async () => {
    if (fetchingRSS) return;
    setFetchingRSS(true);
    setError(null);
    try {
      await sourcesApi.fetch();
      showMessage('Đang thu thập RSS feeds...');
      // Refresh status after a delay
      setTimeout(loadStatus, 3000);
    } catch (err: any) {
      console.error('Fetch RSS failed:', err);
      showMessage(err.message || 'Không thể thu thập RSS', true);
    } finally {
      setFetchingRSS(false);
    }
  };

  const handleResetSignals = async () => {
    if (resetting) return;
    if (!confirm('Reset tất cả signals và articles?\n\nHành động này sẽ:\n1. Đánh dấu tất cả raw_signals là chưa xử lý\n2. Đưa articles trở về trạng thái SIGNAL_COLLECTED\n3. Xóa queue để lấy signals mới\n\nTiếp tục?')) return;

    setResetting(true);
    setError(null);
    try {
      const result = await sourcesApi.resetSignals({
        unprocess_raw_signals: true,
        reset_articles_to_signal_collected: true,
        delete_duplicates: false,
      });
      showMessage(`Đã reset: ${result.raw_signals_reset} signals, ${result.articles_reset} articles`);
      await loadStatus();
    } catch (err: any) {
      console.error('Reset signals failed:', err);
      showMessage(err.message || 'Không thể reset signals', true);
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Đang tải...</div>
      </div>
    );
  }

  const queueByState = status?.queue_by_state || {};
  const failedArticles = status?.failed_articles || [];
  const isPipelineRunning = pipelineInfo?.is_running || false;
  const isContinuous = pipelineInfo?.is_continuous || false;

  return (
    <div className="space-y-6">
      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          {success}
        </div>
      )}

      {/* Header with Pipeline Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
          {/* Status Badge */}
          <div className={clsx(
            'px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2',
            isPipelineRunning 
              ? isContinuous
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-blue-100 text-blue-800 border border-blue-300'
              : 'bg-gray-100 text-gray-600 border border-gray-300'
          )}>
            <span className={clsx(
              'w-2 h-2 rounded-full',
              isPipelineRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            )} />
            {isPipelineRunning 
              ? isContinuous ? 'Continuous Mode' : 'Running'
              : 'Stopped'
            }
          </div>
        </div>
        
        <div className="flex gap-2">
          {/* Fetch RSS Button */}
          <button
            onClick={handleFetchRSS}
            disabled={fetchingRSS}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            {fetchingRSS ? (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            {fetchingRSS ? 'Đang thu thập...' : '📡 Thu thập RSS'}
          </button>
          
          {/* Stop Button */}
          {isPipelineRunning && (
            <button
              onClick={handleStop}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
              </svg>
              Stop
            </button>
          )}
          
          {/* Continuous Mode Button */}
          <button
            onClick={handleStartContinuous}
            disabled={continuousLoading || isPipelineRunning}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors',
              isPipelineRunning && isContinuous
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : isPipelineRunning
                  ? 'bg-gray-400 text-white cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 text-white'
            )}
          >
            {continuousLoading ? (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
            )}
            {isPipelineRunning && isContinuous ? 'Running...' : 'Continuous'}
          </button>
          
          {/* Batch Mode Buttons */}
          <button
            onClick={() => handleRun('normal')}
            disabled={running || isPipelineRunning}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            ▶ Batch Normal
          </button>
          <button
            onClick={() => handleRun('allin')}
            disabled={running || isPipelineRunning}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            ⚡ Batch All-in
          </button>
          <button
            onClick={handleCleanup}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium flex items-center gap-2"
          >
            🗑️ Dọn dẹp
          </button>

          {/* Reset Signals Button */}
          <button
            onClick={handleResetSignals}
            disabled={resetting}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            {resetting ? (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            {resetting ? 'Đang reset...' : '🔄 Reset Signals'}
          </button>
        </div>
      </div>

      {/* Pipeline Stats Panel */}
      {pipelineInfo && (
        <div className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              {/* State */}
              <div className="text-center">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Trạng thái</div>
                <div className={clsx(
                  'text-lg font-bold',
                  isPipelineRunning ? 'text-green-400' : 'text-gray-400'
                )}>
                  {pipelineInfo.state.toUpperCase()}
                </div>
              </div>
              
              {/* Mode */}
              <div className="text-center">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Chế độ</div>
                <div className="text-lg font-bold text-white">
                  {pipelineInfo.mode.toUpperCase()}
                </div>
              </div>
              
              {/* Articles Processed */}
              <div className="text-center">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Đã xử lý</div>
                <div className="text-lg font-bold text-blue-400">
                  {pipelineInfo.stats?.articles_processed || 0}
                </div>
              </div>
              
              {/* Articles Published */}
              <div className="text-center">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Đã đăng</div>
                <div className="text-lg font-bold text-green-400">
                  {pipelineInfo.stats?.articles_published || 0}
                </div>
              </div>
              
              {/* Failed */}
              <div className="text-center">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Thất bại</div>
                <div className="text-lg font-bold text-red-400">
                  {pipelineInfo.stats?.articles_failed || 0}
                </div>
              </div>
            </div>
            
            {/* Started At */}
            {pipelineInfo.started_at && (
              <div className="text-right">
                <div className="text-xs text-gray-400 uppercase tracking-wide">Bắt đầu lúc</div>
                <div className="text-sm text-gray-300">
                  {new Date(pipelineInfo.started_at).toLocaleTimeString('vi-VN')}
                </div>
              </div>
            )}
          </div>
          
          {/* Continuous Mode Progress */}
          {isContinuous && isPipelineRunning && (
            <div className="mt-3 pt-3 border-t border-gray-700">
              <div className="flex items-center gap-2">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: '100%' }}
                  />
                </div>
                <span className="text-xs text-green-400 font-medium flex items-center gap-1">
                  <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running
                </span>
              </div>
            </div>
          )}
          
          {/* No Articles Warning */}
          {isPipelineRunning && status?.queue_size === 0 && (
            <div className="mt-3 pt-3 border-t border-yellow-700">
              <div className="flex items-start gap-2 text-yellow-400">
                <span className="text-lg">⚠️</span>
                <div className="text-sm">
                  <div className="font-medium">Không có articles để xử lý</div>
                  <div className="text-yellow-500 text-xs mt-1">
                    Nhấn "Thu thập RSS" để thu thập tín hiệu mới hoặc đợi scheduler chạy.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pipeline Steps */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Các bước Pipeline</h2>
        <div className="grid grid-cols-4 gap-4">
          {STEPS.map((step) => {
            const count = queueByState[step.key] || 0;
            return (
              <div
                key={step.key}
                className={clsx(
                  'p-4 rounded-lg border-2 transition-all',
                  count > 0 ? STATE_COLORS[step.key] : 'border-gray-200 bg-gray-50'
                )}
              >
                <div className="text-2xl font-bold text-gray-900">
                  {count}
                </div>
                <div className="text-sm font-medium text-gray-700">{step.label}</div>
                <div className="text-xs text-gray-500 mt-1">{step.description}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Queue Status */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Đang chờ xử lý</h3>
          <div className="text-4xl font-bold text-gray-900">
            {status?.queue_size || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Đang chạy</h3>
          <div className="text-4xl font-bold text-blue-600">
            {status?.running || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Thất bại</h3>
          <div className="text-4xl font-bold text-red-600">
            {failedArticles.length}
          </div>
        </div>
      </div>

      {/* Debug Panel - Articles by State */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            🔍 Debug: Số articles theo trạng thái
          </h3>
          <button
            onClick={handleFetchRSS}
            disabled={fetchingRSS}
            className="text-xs text-teal-600 hover:text-teal-700 font-medium disabled:opacity-50"
          >
            {fetchingRSS ? 'Đang thu thập...' : 'Thu thập RSS ngay'}
          </button>
        </div>
        <div className="grid grid-cols-5 gap-2 text-xs">
          {Object.entries(queueByState).map(([state, count]) => {
            const step = STEPS.find(s => s.key === state);
            return (
              <div key={state} className="bg-white rounded p-2 border border-gray-200">
                <div className="font-medium text-gray-600 truncate" title={state}>
                  {step?.label || state.replace(/_/g, ' ')}
                </div>
                <div className="text-2xl font-bold text-gray-900">{count}</div>
              </div>
            );
          })}
        </div>
        {Object.keys(queueByState).length === 0 && (
          <div className="text-sm text-gray-500 text-center py-4">
            Chưa có articles nào trong hệ thống. Nhấn "Thu thập RSS" để bắt đầu.
          </div>
        )}
      </div>

      {/* Failed Articles */}
      {failedArticles.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-red-600">Bài viết thất bại</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {failedArticles.map((article) => (
              <div key={article.id} className="p-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {article.original_title || 'Untitled'}
                  </div>
                    <div className="text-sm text-gray-500 mt-1">
                    Lỗi: {article.last_error ? (
                      <span title={article.last_error}>
                        {article.last_error.split(' ').slice(0, 16).join(' ')}
                        {article.last_error.split(' ').length > 16 ? '...' : ''}
                      </span>
                    ) : article.state}
                  </div>
                  {article.retry_count > 0 && (
                    <div className="text-xs text-gray-400 mt-1">
                      Đã thử lại {article.retry_count} lần
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleRetry(article.id)}
                  className="ml-4 px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  🔄 Thử lại
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pipeline Flow Visualization */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Luồng xử lý</h2>
        <div className="flex items-center justify-between overflow-x-auto pb-2">
          {STEPS.map((step, index) => {
            const count = queueByState[step.key] || 0;
            return (
              <div key={step.key} className="flex items-center">
                <div
                  className={clsx(
                    'px-4 py-3 rounded-lg border-2 min-w-[120px] text-center',
                    count > 0 ? STATE_COLORS[step.key] : 'border-gray-200'
                  )}
                >
                  <div className="text-lg font-bold">{count}</div>
                  <div className="text-xs font-medium">{step.label}</div>
                </div>
                {index < STEPS.length - 1 && (
                  <div className="w-8 h-0.5 bg-gray-300 mx-1 flex-shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
