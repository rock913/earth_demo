<template>
  <div class="app-container">
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="onViewerReady"
    />

    <!-- Act 1: Global Standby -->
    <transition name="fade-up">
      <div v-if="appState === 'standby'" class="intro-screen">
        <h1 class="hero-title">ONE EARTH</h1>
        <p class="subtitle">PLANETARY SPATIAL INTELLIGENCE BASE</p>

        <div class="target-selector">
          <h3>请选择演示任务（Missions）</h3>
          <div class="target-grid">
            <button
              v-for="m in missions"
              :key="m.id"
              @click="lockMission(m)"
              :disabled="!viewerReady"
            >
              <div class="mission-card-title">{{ m.title }}</div>
              <div class="mission-card-sub">{{ m.formula }}</div>
            </button>
          </div>

          <div v-if="!missions?.length" class="mission-empty">
            正在加载 Missions…
          </div>
        </div>
      </div>
    </transition>

    <!-- Act 3: Analyzing HUD -->
    <transition name="slide-down">
      <div v-if="appState === 'analyzing'" class="hud-top">
        <div class="hud-title">ONE EARTH <span>COMMAND</span></div>
        <div class="hud-sub">
          CURRENT MISSION:
          <span class="highlight">{{ currentMission?.name || '—' }}</span>
          /// TARGET:
          <span class="highlight">{{ currentTargetName }}</span>
        </div>
        <div class="hud-status" :class="statusType">{{ statusMsg }}</div>
        <button class="back-btn" @click="resetToStandby">返回全球视角</button>
      </div>
    </transition>

    <transition name="slide-left">
      <HudPanel
        v-if="appState === 'analyzing'"
        :locations="locations"
        :modes="modes"
        :selected-location="selectedLocation"
        :selected-mode="selectedMode"
        :current-location="currentLocationData"
        :is-cached="isCached"
        :loading="loading"
        :exporting="exporting"
        :stats="perfStats"
        :mission="currentMission"
        :zonal-stats="zonalStats"
        :report="reportText"
        :debug-enabled="false"
        :debug-info="null"
        @mode-change="onModeChange"
        @location-change="onLocationChange"
        @cache-export="exportCache"
      />
    </transition>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import CesiumViewer from './components/CesiumViewer.vue'
import HudPanel from './components/HudPanel.vue'
import { apiService } from './services/api.js'

export default {
  name: 'App',
  components: {
    CesiumViewer,
    HudPanel
  },
  
  setup() {
    const cesiumViewer = ref(null)
    const locations = ref({})
    const modes = ref({})
    const missions = ref([])
    const viewerReady = ref(false)

    // Narrative state machine
    // standby: global rotation | flying: target lock dive | analyzing: show HUD + panel
    const appState = ref('standby')
    const selectedMissionId = ref(null)
    const selectedLocation = ref(null)
    const selectedMode = ref('')
    const isCached = ref(false)
    const exporting = ref(false)
    const perfStats = ref(null)
    const zonalStats = ref(null)
    const reportText = ref('')

    // Status box
    const statusMsg = ref('系统待机中...')
    const statusType = ref('idle') // idle | loading | success | error
    const loading = ref(false)

    const currentMission = computed(() => {
      if (!selectedMissionId.value) return null
      return missions.value.find((m) => m.id === selectedMissionId.value) || null
    })
    
    const currentLocationData = computed(() => {
      if (!selectedLocation.value) return null
      return locations.value[selectedLocation.value]
    })

    const currentTargetName = computed(() => {
      return currentLocationData.value?.name || '—'
    })
    
    const initialLocation = computed(() => {
      // Start from a global view (planetary base). We will dive to target after selection.
      return { lat: 35.0, lon: 105.0, height: 20000000 }
    })
    
    onMounted(async () => {
      try {
        // 加载地点/模式/Missions 列表
        const [locs, ms, missionsData] = await Promise.all([
          apiService.getLocations(),
          apiService.getModes(),
          apiService.getMissions()
        ])
        locations.value = locs
        modes.value = ms
        missions.value = missionsData
      } catch (error) {
        console.error('初始化失败:', error)
        alert('后端连接失败，请确保 API 服务已启动 (http://127.0.0.1:8503)')
      }
    })
    
    async function onViewerReady(viewer) {
      viewerReady.value = true
      // Act 1: start global rotation when viewer is ready
      try {
        cesiumViewer.value?.startGlobalRotation?.()
      } catch (_) {
        // ignore
      }
    }

    function normalizeTileUrl(url) {
      if (!url || typeof url !== 'string') return url
      const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8503'
      if (url.startsWith(apiBase + '/')) {
        return url.slice(apiBase.length)
      }
      return url
    }

    function lockMission(mission) {
      if (!viewerReady.value) return
      selectedMissionId.value = mission.id
      selectedLocation.value = mission.location
      selectedMode.value = mission.api_mode
      appState.value = 'flying'
      statusType.value = 'idle'
      statusMsg.value = '目标锁定，正在俯冲...'
      isCached.value = false
      exporting.value = false
      perfStats.value = null
      zonalStats.value = null
      reportText.value = ''

      try {
        cesiumViewer.value?.stopGlobalRotation?.()
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.clearAILayer?.()
      } catch (_) {
        // ignore
      }

      const cam = mission.camera || {}
      const lat = cam.lat
      const lon = cam.lon
      const height = cam.height || 12000
      const duration = cam.duration_s || 3.5

      cesiumViewer.value?.flyTo?.(
        { lat, lon, height },
        duration,
        () => {
          appState.value = 'analyzing'
          statusType.value = 'idle'
          statusMsg.value = '情报展开：正在下发默认指令...'
          // Auto-load the default layer for the mission
          loadLayer(selectedMode.value)
        }
      )
    }

    function resetToStandby() {
      appState.value = 'standby'
      selectedMissionId.value = null
      selectedLocation.value = null
      selectedMode.value = ''
      loading.value = false
      statusType.value = 'idle'
      statusMsg.value = '系统待机中...'
      isCached.value = false
      exporting.value = false
      perfStats.value = null
      zonalStats.value = null
      reportText.value = ''

      try {
        cesiumViewer.value?.clearAILayer?.()
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.startGlobalRotation?.()
      } catch (_) {
        // ignore
      }
    }

    async function loadLayer(modeId) {
      if (!selectedLocation.value) return
      if (!viewerReady.value || !cesiumViewer.value) return

      selectedMode.value = modeId
      loading.value = true
      statusType.value = 'loading'
      const modeName = modes.value?.[modeId] || modeId
      statusMsg.value = `正在生成 [${modeName}] 瓦片...`

      const startTs = Date.now()

      try {
        const layerData = await apiService.getLayer(modeId, selectedLocation.value)
        const url = normalizeTileUrl(layerData.tile_url)
        cesiumViewer.value.loadAILayer(url, 0.85, { fadeIn: true })
        isCached.value = !!layerData.is_cached
        perfStats.value = { loadTime: Date.now() - startTs }
        statusType.value = 'success'
        statusMsg.value = `✅ [${modeName}] 渲染完成`

        // V5: dynamic zonal stats + brief report
        try {
          const statsResp = await apiService.getStats(modeId, selectedLocation.value)
          zonalStats.value = statsResp?.stats || null
        } catch (e) {
          zonalStats.value = null
        }

        try {
          if (currentMission.value && zonalStats.value) {
            const reportResp = await apiService.getReport(currentMission.value.id, zonalStats.value)
            reportText.value = reportResp?.report || ''
          } else {
            reportText.value = ''
          }
        } catch (e) {
          reportText.value = ''
        }
      } catch (e) {
        statusType.value = 'error'
        statusMsg.value = `❌ 渲染失败: ${e?.message || String(e)}`
      } finally {
        loading.value = false
      }
    }

    function onModeChange(modeId) {
      loadLayer(modeId)
    }

    function onLocationChange(locationId) {
      selectedLocation.value = locationId
      if (selectedMode.value) {
        loadLayer(selectedMode.value)
      }
    }

    async function exportCache() {
      if (!selectedLocation.value || !selectedMode.value) return
      exporting.value = true
      try {
        const resp = await apiService.exportCache(selectedMode.value, selectedLocation.value)
        statusType.value = 'success'
        statusMsg.value = `📥 已提交缓存任务: ${resp?.task_id || 'TASK'}`
      } catch (e) {
        statusType.value = 'error'
        statusMsg.value = `❌ 提交缓存任务失败: ${e?.message || String(e)}`
      } finally {
        exporting.value = false
      }
    }
    
    return {
      cesiumViewer,
      locations,
      modes,
      missions,
      initialLocation,
      loading,
      viewerReady,
      appState,
      currentMission,
      currentLocationData,
      currentTargetName,
      selectedMissionId,
      selectedLocation,
      selectedMode,
      isCached,
      exporting,
      perfStats,
      zonalStats,
      reportText,
      statusMsg,
      statusType,
      onViewerReady,
      lockMission,
      resetToStandby,
      loadLayer,
      onModeChange,
      onLocationChange,
      exportCache
    }
  }
}
</script>

<style>
.app-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.intro-screen {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  background: radial-gradient(circle at center, rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.85));
  pointer-events: none;
}

.hero-title {
  margin: 0;
  font-size: 72px;
  letter-spacing: 10px;
  color: #fff;
  text-shadow: 0 0 30px rgba(0, 245, 255, 0.35);
}

.subtitle {
  margin: 10px 0 40px;
  color: #00f5ff;
  letter-spacing: 4px;
}

.target-selector {
  pointer-events: auto;
  background: rgba(10, 15, 25, 0.85);
  border-top: 3px solid #00f5ff;
  border-radius: 8px;
  padding: 22px;
  backdrop-filter: blur(10px);
  color: #fff;
  width: min(520px, 92vw);
}

.target-selector h3 {
  margin: 0 0 14px;
  font-weight: 500;
}

.target-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.target-grid button {
  padding: 14px 14px;
  background: rgba(0, 245, 255, 0.12);
  border: 1px solid rgba(0, 245, 255, 0.35);
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  transition: 0.25s;
  text-align: left;
}

.mission-card-title {
  font-weight: 800;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
}

.mission-card-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}

.mission-empty {
  margin-top: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.target-grid button:hover:enabled {
  background: #00f5ff;
  color: #000;
  box-shadow: 0 0 16px rgba(0, 245, 255, 0.4);
}

.target-grid button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hud-status {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: #dfe;
}

.hud-status.loading {
  color: #ffff66;
  border-color: rgba(255, 255, 102, 0.35);
}

.hud-status.success {
  color: #00ff00;
  border-color: rgba(0, 255, 0, 0.28);
}

.hud-status.error {
  color: #ff6666;
  border-color: rgba(255, 102, 102, 0.28);
}

.controls button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-box {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-box.loading {
  color: #ffff66;
  border-color: rgba(255, 255, 102, 0.5);
}

.status-box.success {
  color: #00ff00;
  border-color: rgba(0, 255, 0, 0.4);
}

.status-box.error {
  color: #ff4444;
  border-color: rgba(255, 68, 68, 0.4);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.8s ease;
}

.fade-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.fade-up-leave-to {
  opacity: 0;
  transform: scale(1.05);
  filter: blur(6px);
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-40px);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 0.15s;
}

.slide-left-enter-from,
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>
