import { useState, useEffect } from 'react';
import { settingsApi, distributionApi, workerTierApi, Settings, AITestResult, ChannelStatus, WorkerTierConfig, WorkerTiersInfo } from '../services/api';
import { useToastStore } from '../store/toast';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingAI, setTestingAI] = useState(false);
  const [aiTestResult, setAiTestResult] = useState<AITestResult | null>(null);
  const [channelStatus, setChannelStatus] = useState<ChannelStatus | null>(null);
  const [togglingChannel, setTogglingChannel] = useState<string | null>(null);

  // Worker Tier State
  const [workerTier, setWorkerTier] = useState<WorkerTierConfig | null>(null);
  const [workerTiers, setWorkerTiers] = useState<WorkerTiersInfo | null>(null);
  const [loadingTier, setLoadingTier] = useState(true);
  const [updatingTier, setUpdatingTier] = useState(false);
  const [pendingTier, setPendingTier] = useState<string | null>(null);
  const { addToast } = useToastStore();

  const loadSettings = async () => {
    try {
      const data = await settingsApi.get();
      setSettings(data);
      setSettingsError(null);
    } catch (error) {
      console.error('Failed to load settings:', error);
      setSettingsError(String(error));
    } finally {
      setLoading(false);
    }
  };

  const loadChannelStatus = async () => {
    try {
      const status = await distributionApi.getChannelStatus();
      setChannelStatus(status);
    } catch (error) {
      console.error('Failed to load channel status:', error);
    }
  };

  const loadWorkerTier = async () => {
    setLoadingTier(true);
    try {
      const [current, all] = await Promise.all([
        workerTierApi.getCurrent(),
        workerTierApi.getAll(),
      ]);
      setWorkerTier(current);
      setWorkerTiers(all);
      // Clear pending tier if it matches current tier
      if (pendingTier === current.tier) {
        setPendingTier(null);
      }
    } catch (error) {
      console.error('Failed to load worker tier:', error);
    } finally {
      setLoadingTier(false);
    }
  };

  const handleSetWorkerTier = async (tier: string) => {
    setUpdatingTier(true);
    try {
      await workerTierApi.setTier(tier);
      setPendingTier(tier); // Track pending tier change
      addToast({
        type: 'success',
        title: 'Đã cập nhật Worker Tier',
        message: `Đã đặt Tier ${tier}. Nhấn "Copy lệnh restart" để áp dụng.`,
      });
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Thất bại',
        message: `Không thể cập nhật tier: ${error}`,
      });
    } finally {
      setUpdatingTier(false);
    }
  };

  useEffect(() => {
    loadSettings();
    loadChannelStatus();
    loadWorkerTier();
  }, []);

  const handleTogglePause = async (channel: 'facebook' | 'twitter') => {
    if (!channelStatus) return;

    setTogglingChannel(channel);
    const isPaused = channel === 'facebook' ? channelStatus.facebook_paused : channelStatus.twitter_paused;

    try {
      if (isPaused) {
        await distributionApi.resumeChannel(channel);
        addToast({
          type: 'success',
          title: 'Đã bật lại',
          message: `Đã bật đăng bài lên ${channel === 'facebook' ? 'Facebook' : 'Twitter'}`,
        });
      } else {
        await distributionApi.pauseChannel(channel);
        addToast({
          type: 'warning',
          title: 'Đã tạm dừng',
          message: `Đã tạm dừng đăng bài lên ${channel === 'facebook' ? 'Facebook' : 'Twitter'}`,
        });
      }
      await loadChannelStatus();
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Thất bại',
        message: `Không thể ${isPaused ? 'bật lại' : 'tạm dừng'} kênh: ${error}`,
      });
    } finally {
      setTogglingChannel(null);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await settingsApi.update(settings);
      addToast({
        type: 'success',
        title: 'Lưu thành công',
        message: 'Cài đặt đã được lưu',
      });
    } catch (error) {
      console.error('Save failed:', error);
      addToast({
        type: 'error',
        title: 'Lưu thất bại',
        message: String(error),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTestAI = async () => {
    if (!settings) return;
    setTestingAI(true);
    setAiTestResult(null);
    try {
      const result = await settingsApi.testAI(
        settings.ai.gateway_url,
        settings.ai.api_key,
        settings.ai.light_model
      );
      setAiTestResult(result);
      if (result.success) {
        addToast({
          type: 'success',
          title: 'Kết nối thành công',
          message: result.message,
        });
      } else {
        addToast({
          type: 'error',
          title: 'Kết nối thất bại',
          message: result.message,
        });
      }
    } catch (error) {
      setAiTestResult({
        success: false,
        message: String(error),
      });
    } finally {
      setTestingAI(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Đang tải...</div>
      </div>
    );
  }

  if (!settings || settingsError) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Cài đặt</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <div className="font-medium text-red-800">Không thể tải cài đặt</div>
              <p className="text-sm text-red-700 mt-1">
                {settingsError || 'Đã xảy ra lỗi khi tải cài đặt. Vui lòng thử tải lại trang.'}
              </p>
              <button
                onClick={() => {
                  setLoading(true);
                  setSettingsError(null);
                  loadSettings();
                }}
                className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium"
              >
                Thử lại
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Tier colors
  const tierColors: Record<string, { bg: string; border: string; text: string; active: string }> = {
    standard: { bg: 'bg-gray-100', border: 'border-gray-300', text: 'text-gray-700', active: 'bg-gray-500' },
    1: { bg: 'bg-gray-100', border: 'border-gray-300', text: 'text-gray-700', active: 'bg-gray-500' },
    2: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700', active: 'bg-blue-500' },
    3: { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-700', active: 'bg-green-500' },
    4: { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-700', active: 'bg-orange-500' },
  };

  const tierLabels: Record<string, { name: string; desc: string }> = {
    standard: { name: 'Standard', desc: '6 workers, ~20 bài/giờ' },
    1: { name: 'Testing', desc: '15 workers, ~200 bài/giờ' },
    2: { name: 'Light', desc: '30 workers, ~600 bài/giờ' },
    3: { name: 'Normal', desc: '45 workers, ~1,200 bài/giờ' },
    4: { name: 'High', desc: '60 workers, ~3,000 bài/giờ' },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Cài đặt</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50"
        >
          {saving ? 'Đang lưu...' : '💾 Lưu cài đặt'}
        </button>
      </div>

      {/* Worker Tier Configuration */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg shadow border border-indigo-100 p-6">
        {/* Docker Restart Info Banner */}
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <div className="font-medium text-amber-800">Cần khởi động lại Docker Worker</div>
              <p className="text-sm text-amber-700 mt-1">
                Khi thay đổi <strong>Worker Tier</strong>, bạn cần chạy lệnh sau trong terminal:
              </p>
              <code className="block mt-2 px-3 py-2 bg-amber-100 rounded text-sm font-mono">
                docker-compose restart worker
              </code>
              <p className="text-xs text-amber-600 mt-2">
                Các cấu hình khác (Scheduler, Pipeline, AI, Distribution) sẽ tự động áp dụng.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-indigo-900 flex items-center gap-2">
              ⚡ Worker Tier Configuration
            </h2>
            <p className="text-sm text-indigo-600 mt-1">
              Điều chỉnh số lượng workers để tăng throughput của pipeline
            </p>
          </div>
          <div className="flex items-center gap-3">
            {workerTier && pendingTier && pendingTier !== workerTier.tier && (
              <div className="px-3 py-1 rounded-lg bg-yellow-100 text-yellow-800 text-sm font-medium">
                Chờ restart: {tierLabels[pendingTier]?.name || pendingTier}
              </div>
            )}
            {workerTier && (
              <div className={`px-4 py-2 rounded-lg font-bold ${tierColors[workerTier.tier]?.bg || 'bg-gray-100'} ${tierColors[workerTier.tier]?.text || 'text-gray-700'}`}>
                Tier {workerTier.tier} - {workerTier.workers} Workers
              </div>
            )}
          </div>
        </div>

        {loadingTier ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-indigo-500">Đang tải cấu hình...</div>
          </div>
        ) : (
          <>
            {/* Tier Selection */}
            <div className="grid grid-cols-5 gap-3 mb-4">
              {['standard', '1', '2', '3', '4'].map((tier) => {
                const isActive = workerTier?.tier === tier;
                const isPending = pendingTier === tier && !isActive;
                const colors = tierColors[tier];
                const labels = tierLabels[tier];
                return (
                  <button
                    key={tier}
                    onClick={() => handleSetWorkerTier(tier)}
                    disabled={updatingTier}
                    className={`
                      relative p-4 rounded-lg border-2 transition-all
                      ${isPending
                        ? 'bg-yellow-50 border-yellow-400 ring-2 ring-yellow-300'
                        : isActive
                        ? `${colors.bg} ${colors.border} border-2 shadow-md`
                        : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }
                      disabled:opacity-50 cursor-pointer
                    `}
                  >
                    <div className={`text-2xl font-bold mb-1 ${isPending ? 'text-yellow-700' : isActive ? colors.text : 'text-gray-700'}`}>
                      {tier}
                    </div>
                    <div className={`text-xs font-medium ${isPending ? 'text-yellow-700' : isActive ? colors.text : 'text-gray-600'}`}>
                      {labels.name}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {tier === 'standard' ? '6' : parseInt(tier) * 15} workers
                    </div>
                    {isPending && (
                      <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs">⏳</span>
                      </div>
                    )}
                    {isActive && (
                      <div className="absolute -top-2 -right-2 w-6 h-6 bg-indigo-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs">✓</span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Pending Changes Warning & Restart Button */}
            {pendingTier && pendingTier !== workerTier?.tier && (
              <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-yellow-700 text-lg">⚠️</span>
                    <span className="text-yellow-800 font-medium">
                      Cấu hình đã thay đổi nhưng chưa được áp dụng
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      // Copy command to clipboard
                      navigator.clipboard.writeText('docker-compose restart worker');
                      addToast({
                        type: 'success',
                        title: 'Đã copy lệnh',
                        message: 'Chạy lệnh này trong terminal để restart worker',
                      });
                    }}
                    className="px-4 py-2 rounded-lg font-medium transition-all bg-indigo-600 hover:bg-indigo-700 text-white"
                  >
                    📋 Copy lệnh restart
                  </button>
                </div>
                <p className="text-sm text-yellow-700 mt-2">
                  Chạy lệnh <code className="bg-yellow-100 px-1 rounded">docker-compose restart worker</code> trong terminal để áp dụng Tier {pendingTier} ({pendingTier === 'standard' ? 6 : parseInt(pendingTier) * 15} workers).
                </p>
              </div>
            )}

            {/* Tier Details */}
            {workerTier && workerTiers && (
              <div className="bg-white rounded-lg p-4 border border-indigo-100">
                <div className="grid grid-cols-2 gap-6">
                  {/* Left: Current Config */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      📊 Cấu hình hiện tại (Tier {workerTier.tier})
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Workers:</span>
                        <span className="font-mono font-medium">{workerTier.workers}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Research:</span>
                        <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                          {workerTier.rate_limits.research}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Write:</span>
                        <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                          {workerTier.rate_limits.write}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Publish:</span>
                        <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                          {workerTier.rate_limits.publish}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Throughput */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      🚀 Throughput ước tính
                    </h3>
                    <div className="text-center p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-100">
                      <div className="text-3xl font-bold text-green-600">
                        ~{workerTier.estimated_throughput.toLocaleString()}
                      </div>
                      <div className="text-sm text-green-600">bài viết / giờ</div>
                    </div>
                    {!pendingTier && (
                      <p className="text-xs text-green-600 mt-2 text-center">
                        ✓ Cấu hình đang hoạt động
                      </p>
                    )}
                    {pendingTier && (
                      <p className="text-xs text-yellow-600 mt-2 text-center">
                        ⏳ Chờ khởi động lại để áp dụng
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Scheduler Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            ⏰ Scheduler
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Khoảng cách thu thập RSS (phút)
              </label>
              <input
                type="number"
                min={1}
                value={settings.scheduler.rss_interval_minutes}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    scheduler: { ...s.scheduler, rss_interval_minutes: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Tần suất thu thập tín hiệu từ các nguồn RSS
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Khoảng cách chạy Pipeline (phút)
              </label>
              <input
                type="number"
                min={1}
                value={settings.scheduler.pipeline_interval_minutes}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    scheduler: { ...s.scheduler, pipeline_interval_minutes: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Tần suất xử lý pipeline cho các bài viết trong hàng đợi
              </p>
            </div>
          </div>
        </div>

        {/* Pipeline Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            ⚙️ Pipeline
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">Auto Publish</div>
                <p className="text-xs text-gray-500">
                  Tự động đăng bài sau khi duyệt
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.pipeline.auto_publish}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      pipeline: { ...s.pipeline, auto_publish: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">Trend Scoring</div>
                <p className="text-xs text-gray-500">
                  Bật đánh giá điểm xu hướng
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.pipeline.trend_scoring_enabled}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      pipeline: { ...s.pipeline, trend_scoring_enabled: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">Governance</div>
                <p className="text-xs text-gray-500">
                  Bật kiểm duyệt nội dung
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.pipeline.governance_enabled}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      pipeline: { ...s.pipeline, governance_enabled: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <div className="border-t pt-4 mt-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    🔥 Trending Only Mode
                  </div>
                  <p className="text-xs text-gray-500">
                    Chỉ xử lý các tin có trend score cao (xu hướng hot)
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.pipeline.trending_only_mode ?? false}
                    onChange={(e) =>
                      setSettings((s) => s && {
                        ...s,
                        pipeline: { ...s.pipeline, trending_only_mode: e.target.checked },
                      })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                </label>
              </div>

              {settings.pipeline.trending_only_mode && (
                <div className="space-y-3 pl-2 border-l-2 border-red-200">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Ngưỡng Trend Score tối thiểu
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min={0.3}
                        max={0.9}
                        step={0.1}
                        value={settings.pipeline.min_trend_score ?? 0.5}
                        onChange={(e) =>
                          setSettings((s) => s && {
                            ...s,
                            pipeline: { ...s.pipeline, min_trend_score: Number(e.target.value) },
                          })
                        }
                        className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <span className="text-sm font-mono bg-red-100 text-red-700 px-2 py-1 rounded min-w-[50px] text-center">
                        {(settings.pipeline.min_trend_score ?? 0.5).toFixed(1)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Cao hơn = chỉ tin hot, Thấp hơn = nhiều tin hơn
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t pt-4 mt-4">
              <div className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                ⏸️ Topic Cooldown
              </div>
              <p className="text-xs text-gray-500 mb-3">
                Giới hạn số bài viết cùng chủ đề trong một khoảng thời gian
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Khoảng thời gian cooldown (giờ)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={24}
                    value={settings.pipeline.topic_cooldown_hours ?? 2}
                    onChange={(e) =>
                      setSettings((s) => s && {
                        ...s,
                        pipeline: { ...s.pipeline, topic_cooldown_hours: Number(e.target.value) },
                      })
                    }
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Tối đa bài/trong khoảng đó
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={settings.pipeline.max_articles_per_topic_per_cooldown ?? 3}
                    onChange={(e) =>
                      setSettings((s) => s && {
                        ...s,
                        pipeline: { ...s.pipeline, max_articles_per_topic_per_cooldown: Number(e.target.value) },
                      })
                    }
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Chế độ mặc định
              </label>
              <select
                value={settings.pipeline.default_mode}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    pipeline: { ...s.pipeline, default_mode: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="fast">Fast - Viết nhanh, ít nghiên cứu</option>
                <option value="normal">Normal - Cân bằng</option>
                <option value="deep">Deep - Nghiên cứu sâu</option>
                <option value="allin">All-in - Không giới hạn</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Thời gian hết hạn tín hiệu (giờ)
              </label>
              <input
                type="number"
                min={1}
                value={settings.pipeline.signal_expiry_hours}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    pipeline: { ...s.pipeline, signal_expiry_hours: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>

        {/* AI Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            🤖 AI Configuration
          </h2>

          {/* Gateway & API Key */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Gateway URL
              </label>
              <input
                type="url"
                value={settings.ai.gateway_url}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    ai: { ...s.ai, gateway_url: e.target.value },
                  })
                }
                placeholder="https://api.openai.com/v1"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                OpenAI, OpenRouter, hoặc OpenAI-compatible API endpoint
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={settings.ai.api_key}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      ai: { ...s.ai, api_key: e.target.value },
                    })
                  }
                  placeholder="sk-..."
                  className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
                <button
                  onClick={handleTestAI}
                  disabled={testingAI || !settings.ai.gateway_url}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium disabled:opacity-50 whitespace-nowrap"
                >
                  {testingAI ? '⏳ Đang test...' : '🔗 Test'}
                </button>
              </div>

              {/* Test Result */}
              {aiTestResult && (
                <div className={`mt-2 p-3 rounded-lg text-sm ${
                  aiTestResult.success
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {aiTestResult.success ? '✓' : '✗'} {aiTestResult.message}
                </div>
              )}
            </div>
          </div>

          {/* Model Configuration */}
          <div className="border-t pt-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-600">Model Configuration</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Researcher Model
              </label>
              <input
                type="text"
                value={settings.ai.researcher_model}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    ai: { ...s.ai, researcher_model: e.target.value },
                  })
                }
                placeholder="claude-3-5-sonnet, gpt-4o, etc."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Model cho nghiên cứu và tìm kiếm thông tin
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Writer Model
              </label>
              <input
                type="text"
                value={settings.ai.writer_model}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    ai: { ...s.ai, writer_model: e.target.value },
                  })
                }
                placeholder="gpt-4o, claude-3-5-sonnet, etc."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Model cho viết bài viết
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Light Model
              </label>
              <input
                type="text"
                value={settings.ai.light_model}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    ai: { ...s.ai, light_model: e.target.value },
                  })
                }
                placeholder="gpt-4o-mini, claude-3-haiku, etc."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Model nhẹ cho phân loại, trending, governance
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Summarizer Model
              </label>
              <input
                type="text"
                value={settings.ai.summarizer_model}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    ai: { ...s.ai, summarizer_model: e.target.value },
                  })
                }
                placeholder="gpt-4o-mini, gpt-3.5-turbo, etc."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Model cho tóm tắt nội dung
              </p>
            </div>
          </div>
        </div>

        {/* WordPress Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            📝 WordPress
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Site URL
              </label>
              <input
                type="url"
                value={settings.wordpress.site_url}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    wordpress: { ...s.wordpress, site_url: e.target.value },
                  })
                }
                placeholder="https://yoursite.com"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                value={settings.wordpress.username}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    wordpress: { ...s.wordpress, username: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                App Password
              </label>
              <input
                type="password"
                value={settings.wordpress.app_password}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    wordpress: { ...s.wordpress, app_password: e.target.value },
                  })
                }
                placeholder="xxxx xxxx xxxx xxxx"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Tạo App Password trong WordPress → Users → Application Passwords
              </p>
            </div>
          </div>
        </div>

        {/* Distribution Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            📤 Distribution
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">📱 Telegram Channel</div>
                <p className="text-xs text-gray-500">Auto-post bài viết lên Telegram</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.distribution?.telegram_channel_enabled ?? true}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      distribution: { ...s.distribution, telegram_channel_enabled: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Telegram Channel ID
              </label>
              <input
                type="text"
                value={settings.distribution?.telegram_channel_id ?? '@linews_vn'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    distribution: { ...s.distribution, telegram_channel_id: e.target.value },
                  })
                }
                placeholder="@linews_vn"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">📘 Facebook Page</div>
                <p className="text-xs text-gray-500">Auto-post bài viết lên Facebook</p>
              </div>
              <div className="flex items-center gap-3">
                {/* Pause/Resume Button */}
                <button
                  onClick={() => handleTogglePause('facebook')}
                  disabled={togglingChannel === 'facebook' || !settings.distribution?.facebook_enabled}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                    settings.distribution?.facebook_enabled
                      ? (channelStatus?.facebook_paused
                          ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300'
                          : 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-300')
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  } disabled:opacity-50`}
                >
                  {togglingChannel === 'facebook' ? '⏳...' : channelStatus?.facebook_paused ? '⏸ Đang tạm dừng' : '▶️ Đang chạy'}
                </button>
                {/* Enable Toggle */}
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.distribution?.facebook_enabled ?? true}
                    onChange={(e) =>
                      setSettings((s) => s && {
                        ...s,
                        distribution: { ...s.distribution, facebook_enabled: e.target.checked },
                      })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">🐦 Twitter/X</div>
                <p className="text-xs text-gray-500">Auto-tweet bài viết</p>
              </div>
              <div className="flex items-center gap-3">
                {/* Pause/Resume Button */}
                <button
                  onClick={() => handleTogglePause('twitter')}
                  disabled={togglingChannel === 'twitter' || !settings.distribution?.twitter_enabled}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                    settings.distribution?.twitter_enabled
                      ? (channelStatus?.twitter_paused
                          ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300'
                          : 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-300')
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  } disabled:opacity-50`}
                >
                  {togglingChannel === 'twitter' ? '⏳...' : channelStatus?.twitter_paused ? '⏸ Đang tạm dừng' : '▶️ Đang chạy'}
                </button>
                {/* Enable Toggle */}
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.distribution?.twitter_enabled ?? true}
                    onChange={(e) =>
                      setSettings((s) => s && {
                        ...s,
                        distribution: { ...s.distribution, twitter_enabled: e.target.checked },
                      })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900"></div>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">📧 Newsletter</div>
                <p className="text-xs text-gray-500">Gửi email digest hàng ngày</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.distribution?.newsletter_enabled ?? true}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      distribution: { ...s.distribution, newsletter_enabled: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Social Media Credentials */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            🔐 Social Media Credentials
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Telegram Bot Token
              </label>
              <input
                type="password"
                value={settings.social?.telegram_bot_token ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, telegram_bot_token: e.target.value },
                  })
                }
                placeholder="123456789:ABCdefGHIjkl..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Lấy từ @BotFather trên Telegram
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Facebook Page ID
              </label>
              <input
                type="text"
                value={settings.social?.facebook_page_id ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, facebook_page_id: e.target.value },
                  })
                }
                placeholder="123456789"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Facebook Access Token
              </label>
              <input
                type="password"
                value={settings.social?.facebook_page_access_token ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, facebook_page_access_token: e.target.value },
                  })
                }
                placeholder="Long-lived token"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Cần quyền pages_manage_posts
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Twitter API Key
              </label>
              <input
                type="password"
                value={settings.social?.twitter_api_key ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, twitter_api_key: e.target.value },
                  })
                }
                placeholder="API Key"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Twitter API Secret
              </label>
              <input
                type="password"
                value={settings.social?.twitter_api_secret ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, twitter_api_secret: e.target.value },
                  })
                }
                placeholder="API Secret"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Twitter Access Token
              </label>
              <input
                type="password"
                value={settings.social?.twitter_access_token ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, twitter_access_token: e.target.value },
                  })
                }
                placeholder="Access Token"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Twitter Access Secret
              </label>
              <input
                type="password"
                value={settings.social?.twitter_access_secret ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    social: { ...s.social, twitter_access_secret: e.target.value },
                  })
                }
                placeholder="Access Token Secret"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>

        {/* Newsletter Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            📧 Newsletter Configuration
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">Bật Newsletter</div>
                <p className="text-xs text-gray-500">Gửi digest cho subscribers</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.distribution?.newsletter_enabled ?? true}
                  onChange={(e) =>
                    setSettings((s) => s && {
                      ...s,
                      distribution: { ...s.distribution, newsletter_enabled: e.target.checked },
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tần suất gửi
              </label>
              <select
                value={settings.newsletter?.frequency ?? 'daily'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    newsletter: { ...s.newsletter, frequency: e.target.value as 'daily' | 'weekly' },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="daily">Hàng ngày</option>
                <option value="weekly">Hàng tuần</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Giờ gửi
              </label>
              <input
                type="time"
                value={settings.newsletter?.send_time ?? '07:00'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    newsletter: { ...s.newsletter, send_time: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SMTP Host
              </label>
              <input
                type="text"
                value={settings.smtp?.smtp_host ?? 'smtp.gmail.com'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, smtp_host: e.target.value },
                  })
                }
                placeholder="smtp.gmail.com"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SMTP Port
              </label>
              <input
                type="number"
                value={settings.smtp?.smtp_port ?? 587}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, smtp_port: Number(e.target.value) },
                  })
                }
                placeholder="587"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SMTP Username
              </label>
              <input
                type="text"
                value={settings.smtp?.smtp_username ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, smtp_username: e.target.value },
                  })
                }
                placeholder="your-email@gmail.com"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SMTP Password
              </label>
              <input
                type="password"
                value={settings.smtp?.smtp_password ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, smtp_password: e.target.value },
                  })
                }
                placeholder="App Password"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Sử dụng App Password thay vì password thường
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Name
              </label>
              <input
                type="text"
                value={settings.smtp?.newsletter_from_name ?? 'Linews'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, newsletter_from_name: e.target.value },
                  })
                }
                placeholder="Linews"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Email
              </label>
              <input
                type="email"
                value={settings.smtp?.newsletter_from_email ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    smtp: { ...s.smtp, newsletter_from_email: e.target.value },
                  })
                }
                placeholder="newsletter@litimez.ai"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>

        {/* SEO & Analytics Settings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            📊 SEO & Analytics
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Google Analytics Measurement ID
              </label>
              <input
                type="text"
                value={settings.seo?.ga_measurement_id ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    seo: { ...s.seo, ga_measurement_id: e.target.value },
                  })
                }
                placeholder="G-XXXXXXXXXX"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Tạo property GA4 trong Google Analytics
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Site URL
              </label>
              <input
                type="url"
                value={settings.seo?.site_url ?? ''}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    seo: { ...s.seo, site_url: e.target.value },
                  })
                }
                placeholder="https://litimez.ai"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Site Name
              </label>
              <input
                type="text"
                value={settings.seo?.site_name ?? 'Linews'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    seo: { ...s.seo, site_name: e.target.value },
                  })
                }
                placeholder="Linews"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="border-t pt-4 mt-4">
              <h3 className="text-sm font-medium text-gray-600 mb-3">Sitemap URLs</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Sitemap:</span>
                  <code className="bg-gray-100 px-2 py-1 rounded">{settings.seo?.site_url ?? 'https://litimez.ai'}/sitemap.xml</code>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">News:</span>
                  <code className="bg-gray-100 px-2 py-1 rounded">{settings.seo?.site_url ?? 'https://litimez.ai'}/sitemap-news.xml</code>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Robots:</span>
                  <code className="bg-gray-100 px-2 py-1 rounded">{settings.seo?.site_url ?? 'https://litimez.ai'}/robots.txt</code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Prediction Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          📈 Prediction System
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Cấu hình hệ thống dự đoán giá và theo dõi alerts
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Symbols theo dõi
            </label>
            <textarea
              value={settings.prediction?.symbols?.map(s => s.symbol).join(', ') ?? 'BTC-USD, ETH-USD, ^VNINDEX'}
              onChange={(e) => {
                const symbols = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                setSettings((s) => s && {
                  ...s,
                  prediction: {
                    ...s.prediction,
                    symbols: symbols.map(symbol => ({
                      symbol,
                      name: symbol,
                      type: symbol.includes('VN') ? 'stock' : 'crypto'
                    }))
                  },
                });
              }}
              placeholder="BTC-USD, ETH-USD, ^VNINDEX"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              rows={2}
            />
            <p className="text-xs text-gray-500 mt-1">
              Danh sách symbols cách nhau bằng dấu phẩy (VD: BTC-USD, ETH-USD, ^VNINDEX)
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Prediction Horizon (days)
              </label>
              <input
                type="number"
                min={1}
                max={30}
                value={settings.prediction?.horizon_days ?? 7}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    prediction: { ...s.prediction, horizon_days: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              />
              <p className="text-xs text-gray-500 mt-1">
                Số ngày dự đoán trước
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Update Frequency
              </label>
              <select
                value={settings.prediction?.update_frequency ?? 'daily'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    prediction: { ...s.prediction, update_frequency: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="hourly">Mỗi giờ</option>
                <option value="daily">Hàng ngày</option>
                <option value="weekly">Hàng tuần</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Cleanup Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          🧹 Cleanup & Retention
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Cấu hình thời gian lưu trữ và dọn dẹp dữ liệu
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Xóa expired signals sau (ngày)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={settings.cleanup?.expired_days ?? 30}
              onChange={(e) =>
                setSettings((s) => s && {
                  ...s,
                  cleanup: { ...s.cleanup, expired_days: Number(e.target.value) },
                })
              }
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Xóa skipped signals sau (ngày)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={settings.cleanup?.skipped_days ?? 7}
              onChange={(e) =>
                setSettings((s) => s && {
                  ...s,
                  cleanup: { ...s.cleanup, skipped_days: Number(e.target.value) },
                })
              }
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Xóa predictions cũ sau (ngày)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={settings.cleanup?.predictions_days ?? 90}
              onChange={(e) =>
                setSettings((s) => s && {
                  ...s,
                  cleanup: { ...s.cleanup, predictions_days: Number(e.target.value) },
                })
              }
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Xóa price history sau (năm)
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={settings.cleanup?.price_history_years ?? 2}
              onChange={(e) =>
                setSettings((s) => s && {
                  ...s,
                  cleanup: { ...s.cleanup, price_history_years: Number(e.target.value) },
                })
              }
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Xóa publish logs sau (ngày)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={settings.cleanup?.publish_logs_days ?? 90}
              onChange={(e) =>
                setSettings((s) => s && {
                  ...s,
                  cleanup: { ...s.cleanup, publish_logs_days: Number(e.target.value) },
                })
              }
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>
      </div>

      {/* Storage Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          💾 Storage & Archive
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Cấu hình thư mục lưu trữ và backup
        </p>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Raw Signals Retention (ngày)
              </label>
              <input
                type="number"
                min={1}
                max={365}
                value={settings.storage?.raw_signals_retention_days ?? 60}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, raw_signals_retention_days: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Articles Retention (ngày)
              </label>
              <input
                type="number"
                min={1}
                max={365}
                value={settings.storage?.articles_retention_days ?? 30}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, articles_retention_days: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Predictions Retention (ngày)
              </label>
              <input
                type="number"
                min={1}
                max={365}
                value={settings.storage?.predictions_retention_days ?? 90}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, predictions_retention_days: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Price History Retention (ngày)
              </label>
              <input
                type="number"
                min={1}
                max={3650}
                value={settings.storage?.price_history_retention_days ?? 730}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, price_history_retention_days: Number(e.target.value) },
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Archive Base Directory
              </label>
              <input
                type="text"
                value={settings.storage?.archive_base_dir ?? '/data/archive'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, archive_base_dir: e.target.value },
                  })
                }
                placeholder="/data/archive"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Backup Base Directory
              </label>
              <input
                type="text"
                value={settings.storage?.backup_base_dir ?? '/data/backup'}
                onChange={(e) =>
                  setSettings((s) => s && {
                    ...s,
                    storage: { ...s.storage, backup_base_dir: e.target.value },
                  })
                }
                placeholder="/data/backup"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Active Categories */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Danh mục hoạt động</h2>
        <p className="text-sm text-gray-500 mb-4">
          Chọn các danh mục sẽ được xử lý trong pipeline
        </p>
        <div className="grid grid-cols-4 gap-3">
          {['công nghệ', 'kinh tế', 'thể thao', 'giải trí', 'sức khỏe', 'giáo dục', 'chính trị', 'quốc tế', 'khám phá', 'ô tô'].map((cat) => (
            <label
              key={cat}
              className="flex items-center gap-2 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={settings.pipeline.active_categories?.includes(cat) || false}
                onChange={(e) => {
                  const cats = settings.pipeline.active_categories || [];
                  setSettings((s) => s && {
                    ...s,
                    pipeline: {
                      ...s.pipeline,
                      active_categories: e.target.checked
                        ? [...cats, cat]
                        : cats.filter((c) => c !== cat),
                    },
                  });
                }}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm capitalize">{cat}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
