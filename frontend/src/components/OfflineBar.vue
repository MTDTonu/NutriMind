<template>
  <!-- 只在「真离线」或「有积压」时出现：其它时候不占版面 -->
  <transition name="ob-slide">
    <div v-if="visible" class="ob" :class="{ danger: offline && pending > 0, quiet: !offline }">
      <span class="ob-dot" />
      <span class="ob-txt">
        <template v-if="offline && pending > 0">离线中 · {{ pending }} 条记录待同步</template>
        <template v-else-if="offline">离线浏览中 · 展示的是上次缓存的数据</template>
        <template v-else-if="syncing">正在同步 {{ pending }} 条离线记录…</template>
        <template v-else>{{ pending }} 条记录待同步</template>
      </span>
      <button v-if="offline === false && !syncing" class="ob-btn" @click="syncNow">立即同步</button>
    </div>
  </transition>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { showToast } from 'vant'
import service from '@/api/request'
import { pendingCount, flushQueue, refreshPending } from '@/utils/offline'

const offline = ref(false)
const syncing = ref(false)
const pending = computed(() => pendingCount.value)

const visible = computed(() => offline.value || pending.value > 0)

function updateOnline() {
  offline.value = !navigator.onLine
}
function refresh() {
  offline.value = !navigator.onLine
  refreshPending()
}

async function syncNow() {
  if (syncing.value) return
  syncing.value = true
  try {
    const r = await flushQueue(service)
    if (r.synced) {
      showToast({ type: 'success', message: `已同步 ${r.synced} 条离线记录` })
    } else if (r.dropped) {
      showToast({ type: 'fail', message: `${r.dropped} 条记录同步失败，请确认后重录` })
    } else {
      showToast({ message: '暂无可同步的记录' })
    }
    await refreshPending()
  } finally {
    syncing.value = false
  }
}

onMounted(() => {
  updateOnline()
  window.addEventListener('online', refresh)
  window.addEventListener('offline', refresh)
})

onUnmounted(() => {
  window.removeEventListener('online', refresh)
  window.removeEventListener('offline', refresh)
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.ob {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  top: 10px;
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 8px 0 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-2);
  font-size: 12.5px;
  color: var(--text-1);
  white-space: nowrap;

  &.danger {
    border-color: var(--clay);
  }

  .ob-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--olive);
    flex-shrink: 0;
  }
  &.danger .ob-dot {
    background: var(--clay);
  }
  &.quiet .ob-dot {
    background: var(--sky);
  }

  .ob-txt {
    line-height: 1;
  }
  .ob-btn {
    height: 24px;
    padding: 0 10px;
    border-radius: 999px;
    border: none;
    background: var(--lime);
    color: var(--on-lime);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }
}

.ob-slide-enter-active,
.ob-slide-leave-active {
  transition: opacity @dur @ease, transform @dur @ease;
}
.ob-slide-enter-from,
.ob-slide-leave-to {
  opacity: 0;
  transform: translate(-50%, -12px);
}

@media (max-width: 1023px) {
  .ob {
    top: 60px;
  }
}
</style>
